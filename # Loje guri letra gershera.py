# Loje guri letra gershera
import random  # always import at the top

zgjedhjet = ["guri", "letra", "gershera"]

while True:
    print("\nOpsione:")
    print("1. Luaj guri letra gershera")
    print("2. Dil")

    opsioni = input("\nZgjidh (1-2): ")

    if opsioni == "2":
        print("Faleminderit qe luajt!")
        break

    if opsioni not in ["1", "2"]:
        print("Zgjedhje e gabuar!")
        continue

    if opsioni == "1":
        kompjuteri = random.choice(zgjedhjet)
        lojtari = input("Zgjidhni guri, letra ose gershera: ").lower().strip()
        
        if lojtari not in zgjedhjet:
            print(f"Zgjedhje e gabuar! Duhet te zgjidhni: {', '.join(zgjedhjet)}")
            continue

        print(f"Kompjuteri zgjodhi: {kompjuteri}")

        if lojtari == kompjuteri:
            print("Barazim!")
        elif (
            (lojtari == "guri" and kompjuteri == "gershera") or
            (lojtari == "letra" and kompjuteri == "guri") or
            (lojtari == "gershera" and kompjuteri == "letra")
        ):
            print("Ju fituat!")
        else:
            print("Kompjuteri fitoi!")