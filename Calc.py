def faktorail(n: int) -> int:
    if n == 0 or n == 1:
        return 1
    else:
        return n * faktorail(n - 1)
    
def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
    
def fuqia(base: int, eksponent: int) -> int:
    if eksponent == 0:
        return 1
    else:
        return base * fuqia(base, eksponent - 1)
    
while True:
    print("\nZgjidhni një funksion:")
    print("1. Faktorail")
    print("2. Fibonacci")
    print("3. Fuqia")
    print("4. Dil nga programi")
    
    zgjedhja = input("Shkruani numrin e funksionit që dëshironi të përdorni: ")
    
    if zgjedhja == "1":
        numri = int(input("Shkruani një numër për të llogaritur faktorailin: "))
        print(f"Faktoraili i {numri} është: {faktorail(numri)}")
    
    elif zgjedhja == "2":
        numri = int(input("Shkruani një numër për të llogaritur Fibonacci: "))
        print(f"Fibonacci i {numri} është: {fibonacci(numri)}")
    
    elif zgjedhja == "3":
        base = int(input("Shkruani bazën: "))
        eksponent = int(input("Shkruani eksponentin: "))
        print(f"{base} në fuqinë {eksponent} është: {fuqia(base, eksponent)}")
    
    elif zgjedhja == "4":
        print("Duke dalë nga programi...")
        break
    
    else:
        print("Zgjedhje e pavlefshme, ju lutem provoni përsëri.")