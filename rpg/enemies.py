import random

class EnemiesMixin:
    def scale_enemy_stats(self, enemy):
        level_bonus = max(0, self.level - 1)
        enemy["hp"] += level_bonus * 15
        enemy["atk"] += level_bonus * 9
        return enemy

    def scale_weapon_stats(self, weapon):
        level_bonus = max(0, self.level - 1)
        weapon["atk"] += level_bonus * 2
        return weapon

    def scale_armor_stats(self, armor):
        level_bonus = max(0, self.level - 1)
        armor["defense"] += level_bonus * 1
        return armor

    def attack(self, enemy):
        damage = random.randint(self.atk - 3, self.atk + 5)
        enemy["hp"] -= damage
        print(f"{self.name} attacks {enemy['name']} for {damage} damage!")

        if enemy["hp"] > 0:
            damage = random.randint(enemy["atk"] - 2, enemy["atk"] + 3) - self.defense
            self.hp -= damage
            print(f"{enemy['name']} attacks {self.name} for {damage} damage!")

    def encounter_enemy(self):
        enemy = random.choice([
            {"name": "Goblin", "hp": 30, "atk": 17},
            {"name": "Orc", "hp": 50, "atk": 22},
            {"name": "Troll", "hp": 80, "atk": 25},
            {"name": "Skeleton", "hp": 40, "atk": 20},
            {"name": "Bandit", "hp": 35, "atk": 18},
            {"name": "Zombie", "hp": 50, "atk": 15},
            {"name": "Vampire", "hp": 60, "atk": 30}
        ])
        enemy = self.scale_enemy_stats(enemy)
        print(f"{self.name} encounters a {enemy['name']}!")

        while self.is_alive() and enemy["hp"] > 0:
            print(f"\n{self.name} - HP: {self.hp}, ATK: {self.atk}")
            print(f"{enemy['name']} - HP: {enemy['hp']}, ATK: {enemy['atk']}")

            while True:
                choice = input("Choose action (attack/use item/run): ").strip().lower()
                if choice in ["attack", "a", "fight", "f"]:
                    self.attack(enemy)
                    break
                if choice in ["run", "r"]:
                    if random.random() < 0.7:
                        print(f"{self.name} escaped from the {enemy['name']}!")
                        return "escaped"
                    damage = max(0, random.randint(enemy["atk"] - 2, enemy["atk"] + 3) - self.defense)
                    self.hp -= damage
                    if damage < 0:
                        damage = 0
                    print(f"Escape failed! {enemy['name']} hits {self.name} for {damage} damage!")
                    break
                if choice in ["use item", "u"]:
                    self.choose_item_to_use()
                    break
                print("Invalid choice. Please enter 'attack', 'use item', or 'run'.")

        if self.is_alive():
            print(f"{self.name} defeated the {enemy['name']}!")
            self.gain_exp(50)
            self.gold += 20
            print(f"{self.name} gains 20 gold!")
            return "won"
        else:
            print(f"{self.name} was defeated by the {enemy['name']}...")
            return "defeated"

    def encounter_item(self):
        item = random.choice([
            "Health Potion",
            "Strength Elixir",
            "Sword",
            "Axe",
            "Bow",
            "Light Armor",
            "Medium Armor",
            "Heavy Armor"])
        print(f"{self.name} finds a {item}!")
        if item in ["Sword", "Axe", "Bow", "Light Armor", "Medium Armor", "Heavy Armor"]:
            if item == "Sword":
                weapon = {"name": "Sword", "atk": 20}
                self.add_weapon(weapon)
            elif item == "Axe":
                weapon = {"name": "Axe", "atk": 15}
                self.add_weapon(weapon)
            elif item == "Bow":
                weapon = {"name": "Bow", "atk": 10}
                self.add_weapon(weapon)
            elif item == "Light Armor":
                armor = {"name": "Light Armor", "defense": 5}
                self.add_armor(armor)
            elif item == "Medium Armor":
                armor = {"name": "Medium Armor", "defense": 10}
                self.add_armor(armor)
            elif item == "Heavy Armor":
                armor = {"name": "Heavy Armor", "defense": 15}
                self.add_armor(armor)
        else:
            self.add_item(item)

    def encounter_boss(self):
        boss = random.choice([
            {"name": "Dragon", "hp": 200, "atk": 40},
            {"name": "Demon Lord", "hp": 150, "atk": 35},
            {"name": "Lich King", "hp": 120, "atk": 30}
        ])
        boss = self.scale_enemy_stats(boss)
        print(f"{self.name} encounters the {boss['name']}!")

        while self.is_alive() and boss["hp"] > 0:
            print(f"\n{self.name} - HP: {self.hp}, ATK: {self.atk}")
            print(f"{boss['name']} - HP: {boss['hp']}, ATK: {boss['atk']}")

            while True:
                choice = input("Choose action (attack/use item/run): ").strip().lower()
                if choice in ["attack", "a", "fight", "f"]:
                    self.attack(boss)
                    break
                if choice in ["run", "r"]:
                    if random.random() < 0.4:
                        print(f"{self.name} barely escaped from the {boss['name']}!")
                        return "escaped"
                    damage = max(0, random.randint(boss["atk"] - 2, boss["atk"] + 3) - self.defense)
                    self.hp -= damage
                    print(f"Escape failed! {boss['name']} strikes {self.name} for {damage} damage!")
                    break
                if choice in ["use item", "u"]:
                    self.choose_item_to_use()
                    break
                print("Invalid choice. Please enter 'attack', 'use item', or 'run'.")

        if self.is_alive():
            print(f"{self.name} defeated the {boss['name']}!")
            self.gain_exp(100)
            self.gold += 50
            print(f"{self.name} gains 50 gold!")
            return "won"
        else:
            print(f"{self.name} was defeated by the {boss['name']}...")
            return "defeated"

    def encounter_gold(self):
        gold_found = random.randint(10, 50)
        self.gold += gold_found
        print(f"{self.name} found {gold_found} gold!")

    def encounter_dungeon(self):
        print(f"{self.name} enters a mysterious dungeon...")
        enemy_encounters = 0

        while self.is_alive():
            dungeon_event = random.choice(["enemy", "item", "gold"])
            if dungeon_event == "enemy":
                enemy_encounters += 1
                outcome = self.encounter_enemy()
                if outcome == "escaped":
                    print(f"{self.name} escapes the dungeon after running from an enemy.")
                    return

                if self.is_alive() and enemy_encounters % 5 == 0:
                    print("A powerful presence appears in the dungeon!")
                    self.encounter_boss()
            elif dungeon_event == "item":
                self.encounter_item()
            else:
                self.encounter_gold()

            if not self.is_alive():
                return

            while True:
                self.status()
                print("\nDungeon options:")
                print("1. Continue exploring the dungeon")
                print("2. Leave the dungeon")
                print("3. Show Inventory")
                print("4. Use Item")
                print("5. Equip Weapon")
                print("6. Equip Armor")
                print("7. Unequip Weapon")
                print("8. Unequip Armor")
                print("9. Short Rest")
                print("10. Save Game")
                print("11. Exit Game")

                action = input("Enter the number of your action: ").strip().lower()

                if action == "1" or action == "continue":
                    print(f"{self.name} explores deeper into the dungeon...")
                    break
                if action == "2" or action == "leave" or action == "l" or action == "exit":
                    print(f"{self.name} leaves the dungeon.")
                    return
                if action == "3" or action == "inventory":
                    self.show_inventory()
                    continue
                if action == "4" or action == "use item":
                    self.choose_item_to_use()
                    continue
                if action == "5" or action == "equip weapon":
                    weapon = self.choose_weapon_to_equip()
                    if weapon:
                        self.equip_weapon(weapon)
                    continue
                if action == "6" or action == "equip armor":
                    armor = self.choose_armor_to_equip()
                    if armor:
                        self.equip_armor(armor)
                    continue
                if action == "7" or action == "unequip weapon":
                    self.unequip_weapon()
                    continue
                if action == "8" or action == "unequip armor":
                    self.unequip_armor()
                    continue
                if action == "9" or action == "short rest":
                    self.short_rest()
                    continue
                if action == "10" or action == "save game":
                    self.save_game()
                    continue
                if action == "11" or action == "exit game":
                    print("Thanks for playing!")
                    exit()

                print("Invalid action. Please try again.")

    def encounter(self):
        encounter_type = random.choice(["enemy", "item", "boss", "gold", "dungeon"])
        if encounter_type == "enemy":
            self.encounter_enemy()
        elif encounter_type == "item":
            self.encounter_item()
        elif encounter_type == "boss":
            self.encounter_boss()
        elif encounter_type == "gold":
            self.encounter_gold()
        else:
            self.encounter_dungeon()

    def move(self, direction):
        print(f"{self.name} moves {direction}.")
        self.encounter()