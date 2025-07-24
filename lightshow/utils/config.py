import json


class Config:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.settings = self.load_config_file()
        self.reload_config()

    def load_config_file(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {self.config_file} not found. Using default settings.")
            return {}

    def reload_config(self):
        self.chunk_size = self.get("chunk_size", 1024)
        self.device_index = self.get("device_index", -2)  # Auto-detect if -1

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def save(self):
        with open(self.config_file, "w") as f:
            self.settings["chunk_size"] = self.chunk_size
            self.settings["device_index"] = self.device_index
            json.dump(self.settings, f, indent=4)
        print(f"Configuration saved to {self.config_file}")
