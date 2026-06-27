from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import BlockedIPRecord
from django.core.cache import cache
import json
import os


class Command(BaseCommand):
    help = 'View and manage blocked IP addresses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='table',
            choices=['table', 'json', 'csv'],
            help='Output format: table, json, or csv'
        )
        parser.add_argument(
            '--permanent-only',
            action='store_true',
            help='Show only permanently blocked IPs'
        )
        parser.add_argument(
            '--export-file',
            type=str,
            help='Export blocked IPs to a file'
        )
        parser.add_argument(
            '--unblock',
            type=str,
            help='Unblock a specific IP address'
        )
        parser.add_argument(
            '--block',
            type=str,
            help='Manually block a specific IP address'
        )

    def handle(self, *args, **options):
        format_type = options['format']
        permanent_only = options.get('permanent_only', False)
        export_file = options.get('export_file')
        unblock_ip = options.get('unblock')
        block_ip = options.get('block')

        # Handle unblock operation
        if unblock_ip:
            self.unblock_ip_address(unblock_ip)
            return

        # Handle manual block operation
        if block_ip:
            self.block_ip_address(block_ip)
            return

        # Get blocked IPs
        queryset = BlockedIPRecord.objects.all()
        if permanent_only:
            queryset = queryset.filter(is_permanently_blocked=True)

        blocked_ips = list(queryset)

        if not blocked_ips:
            self.stdout.write(self.style.SUCCESS('No blocked IP addresses found.'))
            return

        # Export to file if specified
        if export_file:
            self.export_to_file(blocked_ips, export_file, format_type)
            return

        # Display results based on format
        if format_type == 'table':
            self.display_table(blocked_ips)
        elif format_type == 'json':
            self.display_json(blocked_ips)
        elif format_type == 'csv':
            self.display_csv(blocked_ips)

    def display_table(self, blocked_ips):
        """Display blocked IPs in a formatted table."""
        self.stdout.write(self.style.SUCCESS('\n🚫 BLOCKED IP ADDRESSES REPORT'))
        self.stdout.write('=' * 120)
        
        # Header
        header = f"{'IP Address':<20} {'Blocks':<8} {'Status':<20} {'First Blocked':<20} {'Last Blocked':<20} {'Reason':<30}"
        self.stdout.write(self.style.WARNING(header))
        self.stdout.write('-' * 120)

        # Data rows
        for ip in blocked_ips:
            status = "PERMANENT" if ip.is_permanently_blocked else f"TEMP ({ip.block_count})"
            status_color = self.style.ERROR if ip.is_permanently_blocked else self.style.WARNING
            
            # Check if currently in cache (temporarily blocked)
            cache_key = f'blocked_ip:{ip.ip_address}'
            is_temp_blocked = cache.get(cache_key) is not None
            if is_temp_blocked and not ip.is_permanently_blocked:
                status += " [ACTIVE]"
            
            first_blocked = ip.first_blocked.strftime('%Y-%m-%d %H:%M') if ip.first_blocked else 'N/A'
            last_blocked = ip.last_blocked.strftime('%Y-%m-%d %H:%M') if ip.last_blocked else 'N/A'
            reason = (ip.reason[:27] + '...') if len(ip.reason or '') > 30 else (ip.reason or 'Failed login attempts')
            
            row = f"{ip.ip_address:<20} {ip.block_count:<8} {status:<20} {first_blocked:<20} {last_blocked:<20} {reason:<30}"
            
            if ip.is_permanently_blocked:
                self.stdout.write(self.style.ERROR(row))
            elif ip.block_count >= 2:
                self.stdout.write(self.style.WARNING(row))
            else:
                self.stdout.write(row)

        self.stdout.write('-' * 120)
        
        # Summary
        total = len(blocked_ips)
        permanent = len([ip for ip in blocked_ips if ip.is_permanently_blocked])
        warning = len([ip for ip in blocked_ips if ip.block_count >= 2 and not ip.is_permanently_blocked])
        
        self.stdout.write(f'\n📊 SUMMARY:')
        self.stdout.write(f'   Total IPs tracked: {total}')
        self.stdout.write(self.style.ERROR(f'   Permanently blocked: {permanent}'))
        self.stdout.write(self.style.WARNING(f'   Warning level (2+ blocks): {warning}'))
        self.stdout.write(f'   Monitored (1 block): {total - permanent - warning}')

    def display_json(self, blocked_ips):
        """Display blocked IPs in JSON format."""
        data = []
        for ip in blocked_ips:
            data.append({
                'ip_address': ip.ip_address,
                'block_count': ip.block_count,
                'is_permanently_blocked': ip.is_permanently_blocked,
                'first_blocked': ip.first_blocked.isoformat() if ip.first_blocked else None,
                'last_blocked': ip.last_blocked.isoformat() if ip.last_blocked else None,
                'reason': ip.reason or '',
                'is_currently_temp_blocked': cache.get(f'blocked_ip:{ip.ip_address}') is not None
            })
        
        self.stdout.write(json.dumps(data, indent=2))

    def display_csv(self, blocked_ips):
        """Display blocked IPs in CSV format."""
        self.stdout.write('IP Address,Block Count,Is Permanent,First Blocked,Last Blocked,Reason')
        for ip in blocked_ips:
            first_blocked = ip.first_blocked.isoformat() if ip.first_blocked else ''
            last_blocked = ip.last_blocked.isoformat() if ip.last_blocked else ''
            reason = (ip.reason or '').replace(',', ';')  # Escape commas
            self.stdout.write(f'{ip.ip_address},{ip.block_count},{ip.is_permanently_blocked},{first_blocked},{last_blocked},{reason}')

    def export_to_file(self, blocked_ips, filename, format_type):
        """Export blocked IPs to a file."""
        try:
            with open(filename, 'w') as f:
                if format_type == 'json':
                    data = []
                    for ip in blocked_ips:
                        data.append({
                            'ip_address': ip.ip_address,
                            'block_count': ip.block_count,
                            'is_permanently_blocked': ip.is_permanently_blocked,
                            'first_blocked': ip.first_blocked.isoformat() if ip.first_blocked else None,
                            'last_blocked': ip.last_blocked.isoformat() if ip.last_blocked else None,
                            'reason': ip.reason or ''
                        })
                    json.dump(data, f, indent=2)
                elif format_type == 'csv':
                    f.write('IP Address,Block Count,Is Permanent,First Blocked,Last Blocked,Reason\n')
                    for ip in blocked_ips:
                        first_blocked = ip.first_blocked.isoformat() if ip.first_blocked else ''
                        last_blocked = ip.last_blocked.isoformat() if ip.last_blocked else ''
                        reason = (ip.reason or '').replace(',', ';')
                        f.write(f'{ip.ip_address},{ip.block_count},{ip.is_permanently_blocked},{first_blocked},{last_blocked},{reason}\n')
                else:  # table format
                    f.write('BLOCKED IP ADDRESSES REPORT\n')
                    f.write('=' * 120 + '\n')
                    for ip in blocked_ips:
                        status = "PERMANENT" if ip.is_permanently_blocked else f"TEMP ({ip.block_count})"
                        first_blocked = ip.first_blocked.strftime('%Y-%m-%d %H:%M') if ip.first_blocked else 'N/A'
                        last_blocked = ip.last_blocked.strftime('%Y-%m-%d %H:%M') if ip.last_blocked else 'N/A'
                        f.write(f'{ip.ip_address:<20} {ip.block_count:<8} {status:<20} {first_blocked:<20} {last_blocked:<20}\n')
            
            self.stdout.write(self.style.SUCCESS(f'✅ Exported {len(blocked_ips)} blocked IPs to {filename}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to export to {filename}: {e}'))

    def unblock_ip_address(self, ip_address):
        """Unblock a specific IP address."""
        try:
            ip_record = BlockedIPRecord.objects.get(ip_address=ip_address)
            ip_record.is_permanently_blocked = False
            ip_record.reason = f'Manually unblocked by admin at {timezone.now()}'
            ip_record.save()
            
            # Also remove from cache
            cache.delete(f'blocked_ip:{ip_address}')
            
            self.stdout.write(self.style.SUCCESS(f'✅ IP {ip_address} has been unblocked'))
        except BlockedIPRecord.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ IP {ip_address} not found in blocked list'))

    def block_ip_address(self, ip_address):
        """Manually block a specific IP address."""
        ip_record, created = BlockedIPRecord.objects.get_or_create(
            ip_address=ip_address,
            defaults={
                'block_count': 3,
                'is_permanently_blocked': True,
                'reason': f'Manually blocked by admin at {timezone.now()}'
            }
        )
        
        if not created:
            ip_record.is_permanently_blocked = True
            ip_record.reason = f'Manually blocked by admin at {timezone.now()}'
            ip_record.save()
        
        # Add to cache as well
        cache.set(f'blocked_ip:{ip_address}', timezone.now().timestamp() + (24 * 60 * 60), timeout=24 * 60 * 60)
        
        action = 'created and' if created else ''
        self.stdout.write(self.style.SUCCESS(f'✅ IP {ip_address} has been {action} permanently blocked'))