/*
 * International phone inputs.
 *
 * Enhances every <input data-intl-phone> (rendered by core.phone.InternationalPhoneInput)
 * with intl-tel-input: a searchable country/flag selector, automatic country detection
 * from the dialling prefix as the user types or pastes ("+212 6..." selects Morocco),
 * as-you-type formatting and per-country validation backed by libphonenumber.
 *
 * On submit the library fills two hidden inputs, <name>_full (E.164) and <name>_country
 * (ISO2), which the server prefers over the visible value. The server re-validates
 * everything, so if this script or the CDN fails the field degrades to a plain tel input.
 *
 * Public API (window.IntlPhone):
 *   validate(input)      -> boolean, shows/clears the inline message for one input
 *   validateWithin(root) -> boolean, validates every visible phone input inside root
 */
(function () {
    'use strict';

    var ITI_VERSION = '29.5.3';
    var FALLBACK_COUNTRY = 'us';
    var READY_FLAG = 'intlPhoneReady';

    function pageLanguage() {
        return (document.documentElement.getAttribute('lang') || 'en').toLowerCase().split('-')[0];
    }

    // Best guess for an empty field: the region of the browser locale (e.g. "fr-MA" -> "ma").
    function guessCountry() {
        var languages = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''];
        for (var i = 0; i < languages.length; i++) {
            var match = /[-_]([a-z]{2})$/i.exec(languages[i] || '');
            if (match) {
                return match[1].toLowerCase();
            }
        }
        return FALLBACK_COUNTRY;
    }

    // Dropdown labels ("Search", "No results"...) in the page language; English is built in.
    function loadUiTranslations(lang) {
        if (lang === 'en') {
            return Promise.resolve(null);
        }
        var url = 'https://cdn.jsdelivr.net/npm/intl-tel-input@' + ITI_VERSION + '/dist/js/locale/' + lang + '.js';
        return import(url).then(function (module) { return module.default || null; }, function () { return null; });
    }

    function feedbackFor(input) {
        var id = input.id ? input.id + '_feedback' : '';
        var existing = id && document.getElementById(id);
        if (existing) {
            return existing;
        }
        var el = document.createElement('div');
        el.className = 'intl-phone-feedback';
        el.setAttribute('aria-live', 'polite');
        if (id) {
            el.id = id;
            var describedBy = (input.getAttribute('aria-describedby') || '').trim();
            input.setAttribute('aria-describedby', (describedBy ? describedBy + ' ' : '') + id);
        }
        var wrapper = input.closest('.iti') || input;
        wrapper.insertAdjacentElement('afterend', el);
        return el;
    }

    function setFeedback(input, state, message) {
        var el = feedbackFor(input);
        el.textContent = message || '';
        el.classList.toggle('is-error', state === 'error');
        el.classList.toggle('is-ok', state === 'ok');
        el.hidden = !message;
        input.classList.toggle('error', state === 'error');
        input.classList.toggle('intl-phone-invalid', state === 'error');
        if (state === 'error') {
            input.setAttribute('aria-invalid', 'true');
        } else {
            input.removeAttribute('aria-invalid');
        }
    }

    function errorMessage(input, iti) {
        var codes = window.intlTelInput.VALIDATION_ERROR;
        var data = input.dataset;
        switch (iti.getValidationError()) {
            case codes.INVALID_COUNTRY_CODE:
                return data.msgInvalidCountry;
            case codes.TOO_SHORT:
                return data.msgTooShort;
            case codes.TOO_LONG:
                return data.msgTooLong;
            default:
                return data.msgInvalid;
        }
    }

    function detectedCountryMessage(input, iti) {
        var country = iti.getSelectedCountry();
        if (!country || !input.dataset.msgDetected) {
            return '';
        }
        return input.dataset.msgDetected
            .replace('{country}', country.name)
            .replace('{code}', '+' + country.dialCode);
    }

    function hasDigits(input) {
        return /\d/.test(input.value);
    }

    // Validates one input and updates its inline message. Empty optional fields are valid;
    // emptiness of required fields is left to the page's own "required" handling.
    function validate(input) {
        var iti = window.intlTelInput && window.intlTelInput.getInstance(input);
        if (!iti) {
            return true;
        }
        if (!hasDigits(input)) {
            setFeedback(input, null, '');
            return true;
        }
        if (iti.isValidNumberPrecise()) {
            setFeedback(input, 'ok', detectedCountryMessage(input, iti));
            return true;
        }
        setFeedback(input, 'error', errorMessage(input, iti));
        return false;
    }

    function isVisible(el) {
        return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    }

    function validateWithin(root) {
        var firstInvalid = null;
        (root || document).querySelectorAll('input[data-intl-phone]').forEach(function (input) {
            if (isVisible(input) && !validate(input) && !firstInvalid) {
                firstInvalid = input;
            }
        });
        if (firstInvalid) {
            firstInvalid.focus();
            return false;
        }
        return true;
    }

    function enhance(input, uiTranslations) {
        if (input.dataset[READY_FLAG]) {
            return;
        }
        input.dataset[READY_FLAG] = '1';

        var name = input.getAttribute('name') || '';
        var options = {
            initialCountry: input.dataset.initialCountry || guessCountry(),
            separateDialCode: false,
            numberDisplayFormat: 'INTERNATIONAL',
            strictMode: true,
            countrySearch: true,
            countryNameLocale: pageLanguage(),
            hiddenInputs: function () {
                return { phone: name + '_full', country: name + '_country' };
            }
        };
        if (uiTranslations) {
            options.uiTranslations = uiTranslations;
        }
        var iti = window.intlTelInput(input, options);

        var revalidateIfShowingResult = function () {
            var feedback = document.getElementById(input.id + '_feedback');
            if (feedback && !feedback.hidden) {
                validate(input);
            }
        };
        input.addEventListener('blur', function () { validate(input); });
        input.addEventListener('input', revalidateIfShowingResult);
        input.addEventListener('countrychange', revalidateIfShowingResult);

        // Values re-rendered by the server (edit forms, or a submission with errors).
        iti.promise.then(function () {
            if (hasDigits(input)) {
                validate(input);
            }
        });
    }

    // Block submission while a visible phone input is invalid. Registered in the capture
    // phase so it runs before page-level submit handlers (which show loading states).
    function guardSubmit(event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.querySelector('input[data-intl-phone]')) {
            return;
        }
        if (!validateWithin(form)) {
            event.preventDefault();
            event.stopPropagation();
        }
    }

    function init() {
        var inputs = document.querySelectorAll('input[data-intl-phone]');
        if (!inputs.length || !window.intlTelInput) {
            return;
        }
        loadUiTranslations(pageLanguage()).then(function (uiTranslations) {
            inputs.forEach(function (input) { enhance(input, uiTranslations); });
        });
        document.addEventListener('submit', guardSubmit, true);
    }

    window.IntlPhone = { validate: validate, validateWithin: validateWithin };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
