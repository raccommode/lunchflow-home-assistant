# Changelog

## 0.2.0

- Add a Target currency option, including CAD, EUR, and USD.
- Add converted balance, last transaction, and holdings sensors without changing original sensors.
- Use cached daily Frankfurter reference rates, with rate date and original amounts available in entity attributes.
- Isolate exchange-rate failures from original bank data and mark unconvertible amounts unavailable.
- Keep separate entity histories for each target currency.

## 0.1.0

- Initial Lunch Flow Personal API integration for Home Assistant and HACS.
