"""
Utility functions for manual mode user input prompts
"""
import datetime


def prompt_date_range(prompt_message="Enter date range", allow_empty=False, default_days_back=7):
    """Prompt user for date range input

    Args:
        prompt_message (str): Message to display
        allow_empty (bool): Allow empty input (use defaults)
        default_days_back (int): Default number of days to go back if empty

    Returns:
        list: [from_date, to_date] in YYYYMMDD format, or [] if cancelled
    """
    print(f"\n{'='*60}")
    print(f"{prompt_message}")
    print(f"{'='*60}")
    print("Format: YYYYMMDD")
    print("Press Enter without input to use defaults" if allow_empty else "")

    from_date = input("From date (YYYYMMDD): ").strip()

    if not from_date and allow_empty:
        # Use defaults
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=default_days_back)
        from_date = start_date.strftime('%Y%m%d')
        to_date = end_date.strftime('%Y%m%d')
        print(f"Using default range: {from_date} to {to_date} (last {default_days_back} days)")
        return [from_date, to_date]

    if not from_date:
        print("Date required!")
        return []

    to_date = input("To date (YYYYMMDD): ").strip()

    if not to_date:
        print("Date required!")
        return []

    # Validate format
    try:
        datetime.datetime.strptime(from_date, '%Y%m%d')
        datetime.datetime.strptime(to_date, '%Y%m%d')
    except ValueError:
        print("Invalid date format! Use YYYYMMDD")
        return []

    print(f"Date range: {from_date} to {to_date}")
    confirm = input("Confirm? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Cancelled")
        return []

    return [from_date, to_date]


def prompt_single_date(prompt_message="Enter date", allow_today=True):
    """Prompt user for single date input

    Args:
        prompt_message (str): Message to display
        allow_today (bool): Allow empty input to use today

    Returns:
        str: Date in YYYYMMDD format, or None if cancelled
    """
    print(f"\n{'='*60}")
    print(f"{prompt_message}")
    print(f"{'='*60}")
    print("Format: YYYYMMDD")
    if allow_today:
        print("Press Enter to use today's date")

    date_str = input("Date (YYYYMMDD): ").strip()

    if not date_str and allow_today:
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        print(f"Using today: {date_str}")
        return date_str

    if not date_str:
        print("Date required!")
        return None

    # Validate format
    try:
        datetime.datetime.strptime(date_str, '%Y%m%d')
    except ValueError:
        print("Invalid date format! Use YYYYMMDD")
        return None

    print(f"Selected date: {date_str}")
    confirm = input("Confirm? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Cancelled")
        return None

    return date_str


def prompt_integer(prompt_message, default_value=None, min_value=None, max_value=None):
    """Prompt user for integer input

    Args:
        prompt_message (str): Message to display
        default_value (int): Default value if empty
        min_value (int): Minimum allowed value
        max_value (int): Maximum allowed value

    Returns:
        int: User input or default value, or None if cancelled
    """
    print(f"\n{prompt_message}")
    if default_value is not None:
        print(f"Press Enter to use default: {default_value}")

    value_str = input("Value: ").strip()

    if not value_str:
        if default_value is not None:
            print(f"Using default: {default_value}")
            return default_value
        else:
            print("Value required!")
            return None

    try:
        value = int(value_str)
    except ValueError:
        print("Invalid number!")
        return None

    if min_value is not None and value < min_value:
        print(f"Value must be >= {min_value}")
        return None

    if max_value is not None and value > max_value:
        print(f"Value must be <= {max_value}")
        return None

    return value
