from items import ItemsMixin
from enemies import EnemiesMixin
from save_load import SaveLoadMixin

class Player(ItemsMixin, EnemiesMixin, SaveLoadMixin):
    def __init__(self, name):
        self.name = name
        self.hp = 100
        self.atk = 10
        self.defense = 0
        self.inventory = []
        self.gold = 0
        self.level = 1
        self.exp = 0
        self.weapon = None
        self.armor = None

    def is_alive(self):
        return self.hp > 0

    def gain_exp(self, amount):
        self.exp += amount
        print(f"{self.name} gains {amount} EXP!")
        if self.exp >= self.level * 100:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp = 0
        self.hp += 20
        self.atk += 5
        self.defense += 2
        print(f"{self.name} leveled up to level {self.level}!")

    def status(self):
        print(f"{self.name} - HP: {self.hp}, ATK: {self.atk}, DEF: {self.defense}, Level: {self.level}, EXP: {self.exp}, Gold: {self.gold}")

    def sync_equipment_inventory(self):
        if self.weapon and self.weapon["name"] in self.inventory:
            self.inventory.remove(self.weapon["name"])
        if self.armor and self.armor["name"] in self.inventory:
            self.inventory.remove(self.armor["name"])

    def rest(self):
        self.hp = 100 + (self.level - 1) * 20
        print(f"{self.name} rests and restores HP to full!")

    def short_rest(self):
        heal_amount = 20 + (self.level - 1) * 5
        self.hp = min(self.hp + heal_amount, 100 + (self.level - 1) * 20)
        print(f"{self.name} takes a short rest and restores {heal_amount} HP!")