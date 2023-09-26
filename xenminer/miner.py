import json
import requests
import time
from passlib.hash import argon2
import hashlib
from random import choice, randrange
import string
import threading
import re

difficulty = 1
memory_cost = 1500 
cores = 1
account = "0x458782159eAC77e90619143256dF87C957dE38a1"
last_block_url = 'http://xenminer.mooo.com:4445/getblocks/lastblock'

def hash_value(value):
    return hashlib.sha256(value.encode()).hexdigest()

def build_merkle_tree(elements, merkle_tree={}):
    if len(elements) == 1:
        return elements[0], merkle_tree

    new_elements = []
    for i in range(0, len(elements), 2):
        left = elements[i]
        right = elements[i + 1] if i + 1 < len(elements) else left
        combined = left + right
        new_hash = hash_value(combined)
        merkle_tree[new_hash] = {'left': left, 'right': right}
        new_elements.append(new_hash)
    return build_merkle_tree(new_elements, merkle_tree)

from datetime import datetime
def is_within_five_minutes_of_hour():
    timestamp = datetime.now()
    minutes = timestamp.minute
    return 0 <= minutes < 5 or 55 <= minutes < 60

class Block:
    def __init__(self, index, prev_hash, data, valid_hash, random_data, attempts):
        self.index = index
        self.prev_hash = prev_hash
        self.data = data
        self.valid_hash = valid_hash
        self.random_data = random_data
        self.attempts = attempts
        self.timestamp = time.time()
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        sha256 = hashlib.sha256()
        sha256.update(f"{self.index}{self.prev_hash}{self.data}{self.valid_hash}{self.timestamp}".encode("utf-8"))
        return sha256.hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "prev_hash": self.prev_hash,
            "data": self.data,
            "valid_hash": self.valid_hash,
            "random_data": self.random_data,
            "timestamp": self.timestamp,
            "hash": self.hash,
            "attempts": self.attempts
        }

updated_memory_cost = 1500 # just initialize it  ，代表最新的memory_cost

def update_memory_cost_periodically(): # periodically  adv 定期的
    """定期更新内存占用,不同难度值占用的内存不同,这里直接用从服务器获得的难度值代表updated_memory_cost"""
    global memory_cost
    global updated_memory_cost
    time.sleep(10)  # start checking in 10 seconds after launch  启动后10秒开始检查
    while True:
        updated_memory_cost = fetch_difficulty_from_server()
        if updated_memory_cost != memory_cost:
            print(f"Updating difficulty to {updated_memory_cost}")
        time.sleep(60)  # Fetch every 60 seconds

# Function to get difficulty level from the server


def fetch_difficulty_from_server():
    """从矿池获得难度值"""
    try:
        response = requests.get('http://xenminer.mooo.com/difficulty')
        response_data = response.json()
        return str(response_data['difficulty'])
    except Exception as e:
        print(f"An error occurred while fetching difficulty: {e}")
        return '2000'  # Default value if fetching fails

def generate_random_sha256(max_length=128):
    characters = string.ascii_letters + string.digits + string.punctuation
    random_string = ''.join(choice(characters) for _ in range(randrange(1, max_length + 1)))

    sha256 = hashlib.sha256()
    sha256.update(random_string.encode('utf-8'))
    return sha256.hexdigest()

from tqdm import tqdm  #asdf
import time

def submit_pow(account_address, key, hash_to_verify):
    # Download last block record
    url = last_block_url

    try:
        # Attempt to download the last block record
        response = requests.get(url, timeout=10)  # Adding a timeout of 10 seconds
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        print(f"An error occurred: {e}")
        return None  # Optionally return an error value or re-raise the exception

    if response.status_code != 200:
        # Handle unexpected HTTP status codes
        print(f"Unexpected status code {response.status_code}: {response.text}")
        return None  # Optionally return an error value

    if response.status_code == 200:
        records = json.loads(response.text)
        verified_hashes = []

        for record in records:
            block_id = record.get('block_id')
            record_hash_to_verify = record.get('hash_to_verify')
            record_key = record.get('key')
            account = record.get('account')

            # Verify each record using Argon2
            if record_key is None or record_hash_to_verify is None:
                print(f'Skipping record due to None value(s): record_key: {record_key}, record_hash_to_verify: {record_hash_to_verify}')
                continue  # skip to the next record

            if argon2.verify(record_key, record_hash_to_verify):
                verified_hashes.append(hash_value(str(block_id) + record_hash_to_verify + record_key + account))

        # If we have any verified hashes, build the Merkle root
        if verified_hashes:
            merkle_root, _ = build_merkle_tree(verified_hashes)

            # Calculate block ID for output (using the last record for reference)
            output_block_id = int(block_id / 100)

            # Prepare payload for PoW
            payload = {
                'account_address': account_address,
                'block_id': output_block_id,
                'merkle_root': merkle_root,
                'key': key,
                'hash_to_verify': hash_to_verify
            }

            # Send POST request
            pow_response = requests.post('http://xenminer.mooo.com:4446/send_pow', json=payload)

            if pow_response.status_code == 200:
                print(f"Proof of Work successful: {pow_response.json()}")
            else:
                print(f"Proof of Work failed: {pow_response.json()}")

            print(f"Block ID: {output_block_id}, Merkle Root: {merkle_root}")

    else:
        print("Failed to fetch the last block.")

# ANSI escape codes
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

def mine_block(stored_targets, prev_hash):
    global memory_cost  # Make it global so that we can update it
    global updated_memory_cost  # Make it global so that we can receive updates
    found_valid_hash = False
    #memory_cost=fetch_difficulty_from_server()
    argon2_hasher = argon2.using(time_cost=difficulty, salt=b"XEN10082022XEN", memory_cost=memory_cost, parallelism=cores, hash_len = 64)
    attempts = 0
    random_data = None
    start_time = time.time()
    
    with tqdm(total=None, dynamic_ncols=True, desc=f"{GREEN}Mining{RESET}", unit=f" {GREEN}Hashes{RESET}") as pbar:
        while True:
            attempts += 1
        
            if attempts % 100 == 0:
                if updated_memory_cost != memory_cost:
                    memory_cost = updated_memory_cost
                    print(f"{BLUE}Continuing to mine blocks with new difficulty{RESET}")
                    return

            random_data = generate_random_sha256()
            hashed_data = argon2_hasher.hash(random_data + prev_hash)


            for target in stored_targets:
                if target in hashed_data[-87:]:
                # Search for the pattern "XUNI" followed by a digit (0-9)
                    if re.search("XUNI[0-9]", hashed_data) and is_within_five_minutes_of_hour():
                        found_valid_hash = True
                        break
                    elif target == "XEN11":
                        found_valid_hash = True
                        capital_count = sum(1 for char in re.sub('[0-9]', '', hashed_data) if char.isupper())
                        if capital_count >= 65:
                            print(f"{RED}Superblock found{RESET}")
                        break
                    else:
                        found_valid_hash = False
                        break


            pbar.update(1)

            if attempts % 10 == 0:
                elapsed_time = time.time() - start_time
                hashes_per_second = attempts / (elapsed_time + 1e-9)
                pbar.set_postfix({"Difficulty": f"{YELLOW}{memory_cost}{RESET}"}, refresh=True)

            if found_valid_hash:
                print(f"\n{RED}Found valid hash for target {target} after {attempts} attempts{RESET}")
                break


    # Prepare the payload
    payload = {
        "hash_to_verify": hashed_data,
        "key": random_data + prev_hash,
        "account": account,
        "attempts": attempts,
        "hashes_per_second": hashes_per_second
        }

    print (payload)

    max_retries = 2
    retries = 0

    while retries <= max_retries:
        # Make the POST request
        response = requests.post('http://xenminer.mooo.com/verify', json=payload)

        # Print the HTTP status code
        print("HTTP Status Code:", response.status_code)

        if target == "XEN11" and found_valid_hash and response.status_code == 200:
            #submit proof of work validation of last sealed block
            submit_pow(account, random_data + prev_hash, hashed_data)

        if response.status_code != 500:  # If status code is not 500, break the loop
            print("Server Response:", response.json())
            break
        
        retries += 1
        print(f"Retrying... ({retries}/{max_retries})")
        time.sleep(10)  # You can adjust the sleep time


        # Print the server's response
        try:
            print("Server Response:", response.json())
        except Exception as e:
            print("An error occurred:", e)

    return random_data, hashed_data, attempts, hashes_per_second

def verify_block(block):
    argon2_hasher = argon2.using(time_cost=difficulty, memory_cost=memory_cost, parallelism=cores)
    #debug
    print ("Key: ");
    print (block['random_data'] + block['prev_hash'])
    print ("Hash: ");
    print (block['valid_hash'])
    return argon2_hasher.verify(block['random_data'] + block['prev_hash'], block['valid_hash'])


#__name__ 是当前模块名，由于当模块被直接运行时模块名为 __main__ 所以这里的作用是当模块被直接运行时，以下代码块将被运行，当模块是被导入时，代码块不被运行。
if __name__ == "__main__":
    blockchain = []
    stored_targets = ['XEN11', 'XUNI']
    num_blocks_to_mine = 20000000
    
    #Start difficulty monitoring thread
    difficulty_thread = threading.Thread(target=update_memory_cost_periodically)
    difficulty_thread.daemon = True  # This makes the thread exit when the main program exits ，设置线程为守护模式，主线程结束，子线程也结束
    difficulty_thread.start()

    #block的构造函数中有随机值，所以每次运行构造出的Genesis创世块是不同的，也就是说每次运行都会产生一个新的区块链
    genesis_block = Block(0, "0", "Genesis Block", "0", "0", "0")
    blockchain.append(genesis_block.to_dict())
    print(f"Genesis Block: {genesis_block.hash}")

    i = 1
    while i <= num_blocks_to_mine:
        print(f"Mining block {i}...")
        result = mine_block(stored_targets, blockchain[-1]['hash']) #[-1]代表最后一项

        #结果为none或2的时候重回这次循环i不加1，否则i加1
        if result is None:
            print(f"{RED}Restarting mining round{RESET}")
            # Skip the increment of `i` and continue the loop
            continue
        elif result == 2:
            result = None
            continue
        else:
            i += 1

    random_data, new_valid_hash, attempts, hashes_per_second = result
    new_block = Block(i, blockchain[-1]['hash'], f"Block {i} Data", new_valid_hash, random_data, attempts)
    new_block.to_dict()['hashes_per_second'] = hashes_per_second
    blockchain.append(new_block.to_dict())
    print(f"New Block Added: {new_block.hash}")


    # Verification
    for i, block in enumerate(blockchain[1:], 1):
        is_valid = verify_block(block)
        print(f"Verification for Block {i}: {is_valid}")

    # Write blockchain to JSON file
    blockchain_json = json.dumps(blockchain, indent=4)
    with open("blockchain.json", "w") as f:
        f.write(blockchain_json)
