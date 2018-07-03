import json
import pprint
import os
import sys
import subprocess
import time
import base64

from subprocess import PIPE
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5

MIN_PERVOTE_DAILY_PAY = 1000000;
MIN_ACTIVATED_STAKE   = 1500000000000;
CONTINUOUS_RATE       = 0.04879;          # 5% annual rate
PERBLOCK_RATE         = 0.0025;           # 0.25%
STANDBY_RATE          = 0.0075;           # 0.75%
BLOCKS_PER_YEAR       = 52 * 7 * 24 * 2 *3600;   # half seconds per year
SECONDS_PER_YEAR      = 52 * 7 * 24 * 3600;
BLOCKS_PER_DAY        = 2 * 24 * 3600;
BLOCKS_PER_HOUR       = 2 * 3600;
USECONDS_PER_DAY      = 24 * 3600 * 1000000;
USECONDS_PER_YEAR     = SECONDS_PER_YEAR * 1000000;
EOS_TOTAL_SUPPLY      = 10000000000

PRODUCER              = "" # bp name, eg: geosoneforbp
ENCRYPT_PASSWD        = "" # wallet passwd after encrypt by rsa, see: encrypt()

CLEOS_DIR             = "./cleos " #cleos dir
CLEOS_URL             = " -u http://127.0.0.1:18888 " # cleos url

def main():
    try:
        sys.path += [os.path.dirname(os.getcwd()),os.getcwd()]
        cur_path = os.path.abspath(os.path.dirname(__file__))
        root_path = os.path.split(cur_path)[0]
        sys.path.append(root_path)
        reward = calcReward(PRODUCER)
        if reward >= MIN_PERVOTE_DAILY_PAY :
            unlockWallet()
            claimRewards(PRODUCER)
            lockWallet()
    except subprocess.CalledProcessError as e:
        lockWallet()
        log(e)
        log(str(e.stderr, 'utf-8'))

def calcReward(producer):
    states   = getEosioGlobalState()
    producer = getProducerInfo(producer)
    if None == producer :
        return 0
    ct = int(time.time()) * 1000000
    usecs_since_last_fill = float(ct) - float(states['rows'][0]['last_pervote_bucket_fill'])
    if usecs_since_last_fill > 0 and int(states['rows'][0]['last_pervote_bucket_fill']) > 0 :
        new_tokens = int(CONTINUOUS_RATE * EOS_TOTAL_SUPPLY * usecs_since_last_fill / USECONDS_PER_YEAR)
        to_producers       = new_tokens / 5
        to_savings         = new_tokens - to_producers
        to_per_block_pay   = to_producers / 4
        to_per_vote_pay    = to_producers - to_per_block_pay

    producer_per_block_pay = 0
    if int(states['rows'][0]['total_unpaid_blocks']) > 0 :
        producer_per_block_pay = int(float(states['rows'][0]['perblock_bucket']) * float(producer['unpaid_blocks']) / float(states['rows'][0]['total_unpaid_blocks']))
	
    producer_per_vote_pay = 0
    if float(states['rows'][0]['total_producer_vote_weight']) > 0 :
        producer_per_vote_pay  = int(float(states['rows'][0]['pervote_bucket']) * float(producer['total_votes']) / float(states['rows'][0]['total_producer_vote_weight']))

    if producer_per_vote_pay < MIN_PERVOTE_DAILY_PAY :
        producer_per_vote_pay = 0
    amount = producer_per_block_pay + producer_per_vote_pay

    log(amount)

    return amount

def getEosioGlobalState():
    results = cleos('get table eosio eosio global')
    results = json.loads(results.stdout.decode('utf-8'))
    return results

def getProducerInfo(producer = None):
    results = cleos('get  table eosio eosio producers -l 5000')
    results = json.loads(results.stdout.decode('utf-8'))
    if producer is not None:
        rows=results['rows']
        for p in rows:
            if producer == p['owner'] :
                return p
        else:
            return None

def unlockWallet():
    log("run unlockWallet")
    passwd = decrypt(ENCRYPT_PASSWD)
    cmd = 'wallet unlock -n {} --password {}'.format('default', passwd)
    cleos(cmd)

def lockWallet():
    log("run lockWallet")
    cmd = 'wallet lock_all'
    cleos(cmd)

def claimRewards(producer):
    log("run claimRewards")
    cmd = 'system claimrewards {}'.format(producer)
    cleos(cmd)

def encrypt(message):
    with open('public.pem',"r") as f:
        key = f.read()
        rsakey = RSA.importKey(key)
        cipher = Cipher_pkcs1_v1_5.new(rsakey)
        cipher_text = base64.b64encode(cipher.encrypt(message.encode(encoding="utf-8")))
        return cipher_text.decode()

def decrypt(encrypt_message):
    with open('private.pem') as f:
        key = f.read()
        rsakey = RSA.importKey(key)             
        cipher = Cipher_pkcs1_v1_5.new(rsakey)
        message = encrypt_message.encode(encoding="utf-8");
        text = cipher.decrypt(base64.b64decode(message), "ERROR")
        return text.decode()

def log(message):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log = '{} - {}\n'.format(current_time, message)
    print(log)

def cleos(args):
    if isinstance(args, list):
        command = ['{} {} '.format(CLEOS_DIR, CLEOS_URL)]
        command.extend(args)
    else:
        command = CLEOS_DIR + CLEOS_URL + args
    results = subprocess.run(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True, check=True)

    return results

if __name__ == '__main__':
    main()
