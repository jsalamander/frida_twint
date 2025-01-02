# Setup Android

Make sure to root your device first.

Then install mitmproxy according to https://github.com/cyberkernelofficial/mitmproxy-in-termux

```bash
# from termux
proot-distro login ubuntu

apt install mitmproxy python3-pip android-tools-adb -y
 
# copy script into proroot ubuntu
wget https://raw.githubusercontent.com/jsalamander/frida_twint/refs/heads/main/payment_interceptor.py

# start, do not forget to add root CA cert to androids truststore
mitmdump -p 9090 -s payment_interceptor.py

# on first start install the root certificate
pip install frida-tools
# frida server
adb shell
su root
/data/local/tmp/frsf -l 0.0.0.0

# start app
frida -H 192.168.1.3 --codeshare dzonerzy/fridantiroot --codeshare akabe1/frida-multiple-unpinning  -U -f ch.postfinance.twint.android
```