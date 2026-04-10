class ItemsMixin:
    def add_item(self, item):
        self.inventory.append(item)
        print(f"{self.name} obtained {item}!")

    def show_weapons_and_armors_in_inventory(self):
        weapons = [item for item in self.inventory if item in ["Sword", "Axe", "Bow"]]
        armors = [item for item in self.inventory if item in ["Light Armor", "Medium Armor", "Heavy Armor"]]
        print(f"{self.name}'s Weapons: {', '.join(weapons) if weapons else 'None'}")
        print(f"{self.name}'s Armors: {', '.join(armors) if armors else 'None'}")

    def add_weapon(self, weapon):
        self.inventory.append(weapon["name"])
        print(f"{self.name} obtained {weapon['name']}!")

    def add_armor(self, armor):
        self.inventory.append(armor["name"])
        print(f"{self.name} obtained {armor['name']}!")

    def use_item(self, item):
        if item in self.inventory:
            if item == "Health Potion":
                self.inventory.remove(item)
                self.hp += 10
                print(f"{self.name} uses a Health Potion and restores 10 HP!")
            elif item == "Strength Elixir":
                self.inventory.remove(item)
                self.atk += 5
                print(f"{self.name} uses a Strength Elixir and increases ATK by 5!")
            else:
                print(f"{item} cannot be used right now.")
        else:
            print(f"{item} not found in inventory.")

    def equip_weapon(self, weapon):
        if self.weapon is not None:
            print(f"{self.name} already has {self.weapon['name']} equipped. Unequip it first.")
            return
        if weapon["name"] in self.inventory:
            self.inventory.remove(weapon["name"])
        self.weapon = weapon
        self.atk += weapon["atk"]
        print(f"{self.name} equips {weapon['name']} and increases ATK by {weapon['atk']}!")

    def equip_armor(self, armor):
        if self.armor is not None:
            print(f"{self.name} already has {self.armor['name']} equipped. Unequip it first.")
            return
        if armor["name"] in self.inventory:
            self.inventory.remove(armor["name"])
        self.armor = armor
        self.defense += armor["defense"]
        print(f"{self.name} equips {armor['name']} and increases DEF by {armor['defense']}!")

    def choose_weapon_to_equip(self):
        weapons = [item for item in self.inventory if item in ["Sword", "Axe", "Bow"]]
        if not weapons:
            print("No weapons available to equip.")
            return None
        print("Available weapons to equip:")
        for idx, weapon in enumerate(weapons, 1):
            print(f"{idx}. {weapon}")
        choice = input("Enter the number of the weapon to equip: ")
        if choice.isdigit() and 1 <= int(choice) <= len(weapons):
            weapon_name = weapons[int(choice) - 1]
            if weapon_name == "Sword":
                return {"name": "Sword", "atk": 20}
            elif weapon_name == "Axe":
                return {"name": "Axe", "atk": 15}
            elif weapon_name == "Bow":
                return {"name": "Bow", "atk": 10}
            self.inventory.remove(weapon_name)
        else:
            print("Invalid choice.")
            return None

    def choose_armor_to_equip(self):
        armors = [item for item in self.inventory if item in ["Light Armor", "Medium Armor", "Heavy Armor"]]
        if not armors:
            print("No armor available to equip.")
            return None
        print("Available armors to equip:")
        for idx, armor in enumerate(armors, 1):
            print(f"{idx}. {armor}")
        choice = input("Enter the number of the armor to equip: ")
        if choice.isdigit() and 1 <= int(choice) <= len(armors):
            armor_name = armors[int(choice) - 1]
            if armor_name == "Light Armor":
                return {"name": "Light Armor", "defense": 5}
            elif armor_name == "Medium Armor":
                return {"name": "Medium Armor", "defense": 10}
            elif armor_name == "Heavy Armor":
                return {"name": "Heavy Armor", "defense": 15}
            self.inventory.remove(armor_name)
        else:
            print("Invalid choice.")
            return None

    def unequip_weapon(self):
        if self.weapon:
            weapon_name = self.weapon["name"]
            self.atk -= self.weapon["atk"]
            self.inventory.append(weapon_name)
            print(f"{self.name} unequips {weapon_name} and decreases ATK by {self.weapon['atk']}!")
            self.weapon = None
        else:
            print("No weapon equipped.")

    def unequip_armor(self):
        if self.armor:
            armor_name = self.armor["name"]
            self.defense -= self.armor["defense"]
            self.inventory.append(armor_name)
            print(f"{self.name} unequips {armor_name} and decreases DEF by {self.armor['defense']}!")
            self.armor = None
        else:
            print("No armor equipped.")

    def show_inventory(self):
        if self.inventory:
            print(f"{self.name}'s Inventory: {', '.join(self.inventory)}")
        else:
            print(f"{self.name}'s Inventory is empty.")

    def choose_item_to_use(self):
        if not self.inventory:
            print("No items in inventory to use.")
            return

        print(f"{self.name}'s Inventory:")
        for idx, item in enumerate(self.inventory, 1):
            print(f"{idx}. {item}")

        choice = input("Enter the number of the item to use: ")
        if choice.isdigit() and 1 <= int(choice) <= len(self.inventory):
            item_name = self.inventory[int(choice) - 1]
            self.use_item(item_name)
        else:
            print("Invalid choice.")

    def shop(self):
        print(f"{self.name} enters the shop.")
        shop_items = {
            "1": ("Health Potion", 10),
            "2": ("Strength Elixir", 105),
            "3": ("Sword", 50),
            "4": ("Axe", 40),
            "5": ("Bow", 30),
            "6": ("Light Armor", 20),
            "7": ("Medium Armor", 40),
            "8": ("Heavy Armor", 60)
        }
        print("Items available for purchase:")
        for number, (item, price) in shop_items.items():
            print(f"{number}. {item}: {price} gold")

        choice = input("Enter the number of the item to purchase or 'exit' to leave: ").strip().lower()
        if choice in shop_items:
            item_name, item_price = shop_items[choice]
            if self.gold >= item_price:
                self.gold -= item_price
                if item_name == "Health Potion":
                    self.add_item("Health Potion")
                elif item_name == "Strength Elixir":
                    self.add_item("Strength Elixir")
                elif item_name == "Sword":
                    weapon = {"name": "Sword", "atk": 20}
                    self.add_weapon(weapon)
                elif item_name == "Axe":
                    weapon = {"name": "Axe", "atk": 15}
                    self.add_weapon(weapon)
                elif item_name == "Bow":
                    weapon = {"name": "Bow", "atk": 10}
                    self.add_weapon(weapon)
                elif item_name == "Light Armor":
                    armor = {"name": "Light Armor", "defense": 5}
                    self.add_armor(armor)
                elif item_name == "Medium Armor":
                    armor = {"name": "Medium Armor", "defense": 10}
                    self.add_armor(armor)
                elif item_name == "Heavy Armor":
                    armor = {"name": "Heavy Armor", "defense": 15}
                    self.add_armor(armor)
                print(f"{self.name} purchased {item_name} for {item_price} gold!")
            else:
                print("Not enough gold to purchase that item.")
        elif choice == 'exit':
            print("Exiting the shop.")
        else:
            print("Invalid item. Please try again.")

    def sell(self, item):
        sell_prices = {
            "Health Potion": 5,
            "Strength Elixir": 50,
            "Sword": 25,
            "Axe": 20,
            "Bow": 15,
            "Light Armor": 10,
            "Medium Armor": 20,
            "Heavy Armor": 30,
        }

        if item in self.inventory:
            if item not in sell_prices:
                print(f"{item} cannot be sold.")
                return

            self.gold += sell_prices[item]
            self.inventory.remove(item)
            print(f"{self.name} sold {item} for {sell_prices[item]} gold!")
        else:
            print(f"{item} not found in inventory.")

    def choose_item_to_sell(self):
        if not self.inventory:
            print("No items in inventory to sell.")
            return

        print(f"{self.name}'s Inventory:")
        for idx, item in enumerate(self.inventory, 1):
            print(f"{idx}. {item}")

        choice = input("Enter the number of the item to sell: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(self.inventory):
            item_name = self.inventory[int(choice) - 1]
            self.sell(item_name)
        else:
            print("Invalid choice.")

    def sell_duplicate_items(self):
        item_counts = {}
        for item in self.inventory:
            item_counts[item] = item_counts.get(item, 0) + 1

        for item, count in item_counts.items():
            if count > 1:
                duplicates = count - 1
                for _ in range(duplicates):
                    self.sell(item)