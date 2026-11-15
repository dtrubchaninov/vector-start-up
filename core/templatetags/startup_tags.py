from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def money(value, symbol='₽'):
    """Format decimal/number as space-grouped tabular currency string: 1 250 000 ₽."""
    if value is None or value == '':
        return f'0 {symbol}'
    try:
        num = Decimal(str(value))
    except Exception:
        return f'{value} {symbol}'
    formatted = f'{num:,.0f}'.replace(',', ' ')
    if symbol in ('$', '€'):
        return f'{symbol}{formatted}'
    return f'{formatted} {symbol}'


@register.filter
def money_compact(value, symbol='₽'):
    """Compact formatting for high-level KPI cards (e.g. 12,4 млн ₽)."""
    if value is None or value == '':
        return f'0 {symbol}'
    try:
        num = float(value)
    except Exception:
        return f'{value} {symbol}'
    abs_num = abs(num)
    if abs_num >= 1_000_000:
        short = f'{num / 1_000_000:.2f}'.rstrip('0').rstrip('.').replace('.', ',')
        return f'{short} млн {symbol}' if symbol == '₽' else f'{symbol}{short}M'
    if abs_num >= 100_000:
        short = f'{num / 1_000:.0f}'
        return f'{short} тыс. {symbol}' if symbol == '₽' else f'{symbol}{short}K'
    return money(value, symbol)


@register.filter
def clamp_pct(value):
    """Clamp percentage to [0, 100] for CSS width styles."""
    try:
        v = float(value)
    except Exception:
        return 0
    return round(max(0.0, min(v, 100.0)), 1)


@register.filter
def format_metric(value, unit=''):
    """Format KPI value neatly with unit."""
    if value is None:
        return '0'
    try:
        num = Decimal(str(value))
        if num == num.to_integral():
            text = f'{num:,.0f}'.replace(',', ' ')
        else:
            text = f'{num:,.1f}'.replace(',', ' ').replace('.', ',')
    except Exception:
        text = str(value)
    if not unit:
        return text
    if unit in ('$', '€'):
        return f'{unit}{text}'
    if unit == '%':
        return f'{text}%'
    return f'{text} {unit}'
