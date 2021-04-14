import json
import matplotlib.pyplot as plt
from os.path import abspath
import platform
import requests
import time
import traceback

plat = platform.system()

if plat == "Linux":
    import subprocess
elif plat == "Windows":
    import ctypes
else:
    print("Currently unsupported OS, shouldn't be too hard to add yourself though!")


class SetBackground():
    def __init__(self, conf_path, plat):
        self.conf_path = conf_path

        self.img_name = "chart.png"
        self.last_price = -1

        self.plat = plat

    def set_wallpaper(self):
        img_path = abspath(self.img_name)
        if self.plat == "Windows":
            ctypes.windll.user32.SystemParametersInfoW(0x14, 0, img_path, 0)

        if self.plat == "Linux":
            args = self.conf["background_cmd"].split()
            for x, arg in enumerate(args):
                if arg == "PIC":
                    args[x] = img_path

            if img_path not in args:
                raise Exception(
                    'Image path is not present in config, remember to have "PIC" as an argument.')

            try:
                subprocess.check_call(args)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise Exception(
                    f'{e}\nError when changing wallpaper, correctly modify "background_cmd" in the config.')

    def reload_conf(self):
        self.conf = json.loads(open(self.conf_path, "r").read())

        self.coin, self.symbol, self.name = self.get_coin_info(
            self.conf["coin"])

        self.currency = self.conf["currency"].upper()
        self.timespan = self.conf["timespan"]

        if self.conf["dark_theme"]:
            plt.style.use("dark_background")

    def get_coin_info(self, coin):
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin}?localization=false&tickers=false&market_data=false&community_data=false&developer_data=false")

        try:
            res = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            raise json.decoder.JSONDecodeError(
                f"Failed to decode response: {r.text}")

        if "error" in res:
            raise Exception(res["error"])

        symbol = res["symbol"]
        name = res["name"]

        return coin, symbol, name

    def get_prices(self):
        if self.timespan == "max" or self.timespan == 0:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{self.coin}/market_chart?vs_currency={self.currency}&days=max")
        else:
            to_h = time.time()
            from_h = to_h - (self.timespan * 3600)
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{self.coin}/market_chart/range?vs_currency={self.currency}&from={from_h}&to={to_h}")

        try:
            res = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            raise json.decoder.JSONDecodeError(
                f"Failed to decode response: {r.text}")

        if "error" in res:
            raise Exception(res["error"])

        return res["prices"]

    def create_image(self, prices, curr_price):
        self.last_price = curr_price

        x = [x for x in range(len(prices))]
        y = [x[1] for x in prices]

        plt.figure(figsize=(self.conf["figsize"][0], self.conf["figsize"][1]))

        if "auto" in self.conf["color"]:
            if y[-1] >= y[0]:
                plt.plot(x, y, color="#4eaf0a")
            else:
                plt.plot(x, y, color="#e15241")
        else:
            plt.plot(x, y, color=self.conf["color"])

        plt.ylabel(f"Price in {self.currency}")

        title_str = f"Price chart for {self.name}\n1 {self.symbol.upper()} = {curr_price} {self.currency}\n"

        highest = max(y)
        lowest = min(y)

        if highest > 10:
            title_str += f"High: {highest:.2f} {self.currency}    "
        else:
            title_str += f"High: {highest:.8f} {self.currency}    "

        if lowest > 10:
            title_str += f"Low: {lowest:.2f} {self.currency}\n"
        else:
            title_str += f"Low: {lowest:.8f} {self.currency}\n"

        plt.title(title_str)
        plt.tick_params(bottom=False, labelbottom=False)

        plt.savefig(self.img_name, dpi=self.conf["dpi"])
        plt.close()

    def loop(self):
        while True:
            self.reload_conf()

            prices = self.get_prices()

            try:
                curr_price = prices[-1][-1]
                if curr_price > 10:
                    curr_price = format(curr_price, ".2f")
                else:
                    curr_price = format(curr_price, ".8f")
            except TypeError:
                curr_price = None
            except IndexError:
                raise Exception(
                    "The selected coin doesn't have any price history in the selected range")

            if prices != None and curr_price != None and self.last_price != curr_price:
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(prices[-1][0]/1000)),
                      "-", curr_price, self.currency)

                self.create_image(prices, curr_price)
                self.set_wallpaper()

            time.sleep(self.conf["refresh_interval"])


if __name__ == "__main__":
    while True:
        try:
            SetBackground("config.json", plat).loop()
        except requests.exceptions.ConnectionError:
            print("No internet connection.")
            time.sleep(5)
        except Exception:
            traceback.print_exc()
            time.sleep(2)
