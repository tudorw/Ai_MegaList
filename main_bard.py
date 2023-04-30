import click
from flask import Flask, request, jsonify
from web3 import Web3
from solc import compile_source
from eth_account import Account
from web3.exceptions import ValidationError, TimeExhausted

# Set up Flask app
app = Flask(__name__)

# Connect to Fantom blockchain
w3 = Web3(Web3.HTTPProvider("https://rpc.ftm.tools"))

# Load and compile smart contract
with open("my_smart_contract.sol", "r") as file:
    contract_source_code = file.read()

compiled_contract = compile_source(contract_source_code)
contract_interface = compiled_contract['<stdin>:MySmartContract']
abi = contract_interface["abi"]
bytecode = contract_interface["bin"]

def get_contract_instance(contract_address):
    return w3.eth.contract(address=contract_address, abi=abi)


# API endpoint to deploy the smart contract
@app.route("/deploy", methods=["POST"])
@click.command("deploy")
def deploy():
    try:
        private_key = request.json["private_key"]

    # Deploy the contract
    account = Account.from_key(private_key)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.getTransactionCount(account.address)
    txn = contract.constructor().buildTransaction({
        'from': account.address,
        'gas': 1500000,
        'gasPrice': w3.eth.gasPrice,
        'nonce': nonce,
    })

    signed_txn = account.sign_transaction(txn)
    txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    txn_receipt = w3.eth.waitForTransactionReceipt(txn_hash)

    return jsonify({'contract_address': txn_receipt['contractAddress']})
    except (ValidationError, TimeExhausted) as e:
        return jsonify({"error": str(e)}), 400

# API endpoint to read data from the smart contract
@app.route("/read", methods=["GET"])
@click.command("read")
def read_data():
    try:
        contract_address = request.args.get("contract_address")
    	contract = get_contract_instance(contract_address)
	result = contract.functions.myFunction().call()
    	return jsonify({"data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# API endpoint to write data to the smart contract
@app.route("/write", methods=["POST"])
@click.command("write")
def write_data():
    try:
        contract_address = request.json["contract_address"]
    private_key = request.json["private_key"]
    # Replace with the appropriate function arguments
    function_args = request.json["function_args"]

    account = Account.from_key(private_key)
    contract = get_contract_instance(contract_address)
    nonce = w3.eth.getTransactionCount(account.address)

    txn = contract.functions.myFunction(*function_args).buildTransaction({
        'from': account.address,
        'gas': 1500000,
        'gasPrice': w3.eth.gasPrice,
        'nonce': nonce,
    })

    signed_txn = account.sign_transaction(txn)
    txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    txn_receipt = w3.eth.waitForTransactionReceipt(txn_hash)

    return jsonify({"transaction_hash": txn_hash.hex()})
    except (ValidationError, TimeExhausted) as e:
        return jsonify({"error": str(e)}), 400

# API endpoint to get events emitted
@app.route("/events", methods=["GET"])
@click.command("events")
def get_events():
    try:
        contract_address = request.args.get("contract_address")
    event_name = request.args.get("event_name")
    from_block = int(request.args.get("from_block", 0))
    to_block = request.args.get("to_block", "latest")

    contract = get_contract_instance(contract_address)
    event_filter = contract.events[event_name].createFilter(
        fromBlock=from_block,
        toBlock=to_block,
    )
    events = event_filter.get_all_entries()

    return jsonify({"events": events})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
