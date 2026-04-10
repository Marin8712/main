import json

class SaveLoadMixin:
    def save_game(self):
        save_data = {
            "name": self.name,
            "hp": self.hp,
            "atk": self.atk,
            "defense": self.defense,
            "inventory": self.inventory,
            "gold": self.gold,
            "level": self.level,
            "exp": self.exp,
            "weapon": self.weapon,
            "armor": self.armor
        }
        with open(f"{self.name}_save.json", "w") as save_file:
            json.dump(save_data, save_file)
        print(f"Game saved for {self.name}!")

    def load_game(self, filename):
        try:
            with open(filename, "r") as save_file:
                save_data = json.load(save_file)
                self.name = save_data["name"]
                self.hp = save_data["hp"]
                self.atk = save_data["atk"]
                self.defense = save_data["defense"]
                self.inventory = save_data["inventory"]
                self.gold = save_data["gold"]
                self.level = save_data["level"]
                self.exp = save_data["exp"]
                self.weapon = save_data["weapon"]
                self.armor = save_data["armor"]
                self.sync_equipment_inventory()
            print(f"Game loaded for {self.name}!")
        except FileNotFoundError:
            print("Save file not found.")