def factorial(n):
    """
    Calculate the factorial of a number recursively.
    
    Args:
        n (int): A non-negative integer
        
    Returns:
        int: The factorial of n (n!)
        
    Raises:
        ValueError: If n is negative
        TypeError: If n is not an integer
    """
    # Input validation
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    
    # Base cases
    if n == 0 or n == 1:
        return 1
    
    # Recursive case
    return n * factorial(n - 1)


# Example usage
if __name__ == "__main__":
    # Test the function with a few examples
    test_values = [0, 1, 2, 3, 4, 5, 10]
    
    print("Factorial calculations:")
    for val in test_values:
        result = factorial(val)
        print(f"{val}! = {result}")
    
    # Example of error handling
    try:
        factorial(-1)
    except ValueError as e:
        print(f"Error: {e}")
    
    try:
        factorial(3.5)
    except TypeError as e:
        print(f"Error: {e}")