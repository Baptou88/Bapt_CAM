def format_float(value, max_decimals=4):
    return str(round(value, max_decimals)).rstrip("0").rstrip(".")


if __name__ == "__main__":
    print(format_float(1.23456789))  # Output: "1.2346"
    print(format_float(1.00000000))  # Output: "1"
    print(format_float(0.00000001))  # Output: "0"
    print(format_float(123.456789, max_decimals=2))  # Output: "123.46"
