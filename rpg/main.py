import json
from player import Player

def main():
    while True:
        print("You are finally awake.")
        print("Welcome to the Text-Based RPG!")
        print("What would you like to do?")
        print("1. Start New Game")
        print("2. Load Game")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            player_name = input("Enter your character's name: ")
            hero = Player(player_name)
            break
        elif choice == "2":
            filename = input("Enter the filename to load: ")
            if save_file := f"{filename}_save.json":
                try:
                    with open(save_file, "r") as f:
                        save_data = json.load(f)
                        hero = Player(save_data["name"])
                        hero.hp = save_data["hp"]
                        hero.atk = save_data["atk"]
                        hero.defense = save_data["defense"]
                        hero.inventory = save_data["inventory"]
                        hero.gold = save_data["gold"]
                        hero.level = save_data["level"]
                        hero.exp = save_data["exp"]
                        hero.weapon = save_data["weapon"]
                        hero.armor = save_data["armor"]
                        hero.sync_equipment_inventory()
                    print(f"Game loaded for {hero.name}!")
                    break
                except FileNotFoundError:
                    print("Save file not found. Please try again.")
            hero = Player("")
            hero.load_game(filename)
            break
        else:
            print("Invalid choice. Please try again.")

    while hero.is_alive():
        hero.status()
        print("\nWhat would you like to do?")
        print("1. Move")
        print("2. Show Inventory")
        print("3. Use Item")
        print("4. Equip Weapon")
        print("5. Equip Armor")
        print("6. Unequip Weapon")
        print("7. Unequip Armor")
        print("8. Shop")
        print("9. Sell Item")
        print("10. Sell Duplicates")
        print("11. Rest")
        print("12. Save Game")
        print("13. Load Game")
        print("14. Exit Game")
        action = input("Enter the number of your action: ").lower()

        if action == "1" or action == "move":
            direction = input("Enter direction to move (north, south, east, west): ").lower()
            hero.move(direction)
        elif action == "2" or action == "inventory":
            hero.show_inventory()
        elif action == "3" or action == "use item":
            hero.choose_item_to_use()
        elif action == "4" or action == "equip weapon":
            weapon = hero.choose_weapon_to_equip()
            if not weapon:
                continue
            hero.equip_weapon(weapon)
        elif action == "5" or action == "equip armor":
            armor = hero.choose_armor_to_equip()
            if not armor:                
                continue
            hero.equip_armor(armor)
        elif action == "6" or action == "unequip weapon":
            hero.unequip_weapon()
        elif action == "7" or action == "unequip armor":
            hero.unequip_armor()
        elif action == "8" or action == "shop":
            hero.shop()
        elif action == "9" or action == "sell item":
            hero.choose_item_to_sell()
        elif action == "10" or action == "sell duplicates":
            hero.sell_duplicate_items()
        elif action == "11" or action == "rest":
            hero.rest()
        elif action == "12" or action == "save game":
            hero.save_game()
        elif action == "13" or action == "load game":
            filename = input("Enter the filename to load: ")
            hero.load_game(filename)
        elif action == "14" or action == "exit":
            print("Thanks for playing!")
            break
        else:
            print("Invalid action. Please try again.")

    while True:
        retry = input("Game Over! Do you want to play again? (yes/no): ").lower()
        if retry == "yes":
            main()
            break
        elif retry == "no":
            print("Thanks for playing!")
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

if __name__ == "__main__":    
    main()