"""Shared default avatar (inline SVG data URI) used when a user has no picture."""

# Teal circle with a white user silhouette — renders anywhere, no static file needed.
DEFAULT_AVATAR = (
    "data:image/svg+xml,"
    "%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20128%20128'%3E"
    "%3Crect%20width='128'%20height='128'%20rx='64'%20fill='%236CA8C9'/%3E"
    "%3Ccircle%20cx='64'%20cy='50'%20r='26'%20fill='white'/%3E"
    "%3Cpath%20d='M22%20114c0-23%2019-36%2042-36s42%2013%2042%2036z'%20fill='white'/%3E"
    "%3C/svg%3E"
)
