from flask import Flask, jsonify, request
import requests
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from protobuf_decoder.protobuf_decoder import Parser
from datetime import datetime
import json

app = Flask(__name__)

DEFAULT_UID = "3197059560"
DEFAULT_PASS = "3EC146CD4EEF7A640F2967B06D7F4413BD4FB37382E0ED260E214E8BACD96734"
JWT_GEN_URL = "https://ariflexlabs-jwt-gen.onrender.com/fetch-token"

def get_jwt():
    try:
        params = {'uid': DEFAULT_UID, 'password': DEFAULT_PASS}
        response = requests.get(JWT_GEN_URL, params=params)
        if response.status_code == 200:
            jwt_data = response.json()
            return jwt_data.get("JWT TOKEN")
        return None
    except:
        return None

def Encrypt_ID(x):
    x = int(x)
    dec = ['{:02x}'.format(i + 128) for i in range(128)]
    xxx = ['{:02x}'.format(i) for i in range(1, 128)]
    x = x / 128
    if x > 128:
        x = x / 128
        if x > 128:
            x = x / 128
            if x > 128:
                x = x / 128
                return dec[int(((((x - int(x)) * 128 - int(((x - int(x)) * 128))) * 128 - int(((((x - int(x)) * 128 - int(((x - int(x)) * 128))) * 128))) * 128)))] + \
                       dec[int((((x - int(x)) * 128 - int(((x - int(x)) * 128))) * 128 - int(((((x - int(x)) * 128 - int(((x - int(x)) * 128))) * 128)))))] + \
                       dec[int(((x - int(x)) * 128 - int(((x - int(x)) * 128))))] + \
                       dec[int((x - int(x)) * 128)] + xxx[int(x)]
            else:
                return dec[int((((x - int(x)) * 128 - int((x - int(x)) * 128)) * 128))] + \
                       dec[int(((x - int(x)) * 128 - int((x - int(x)) * 128)))] + \
                       dec[int((x - int(x)) * 128)] + xxx[int(x)]

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()

def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type in ["varint", "string"]:
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = parse_results(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def get_available_room(input_text):
    parsed_results = Parser().parse(input_text)
    parsed_results_dict = parse_results(parsed_results)
    return json.dumps(parsed_results_dict)

@app.route('/api/player-info', methods=['GET'])
def get_player_info():
    try:
        player_id = request.args.get('id')
        if not player_id:
            return jsonify({"status": "error", "message": "Player ID is required", "credits": "TEAM-AKIRU", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}), 400

        jwt_token = get_jwt()
        if not jwt_token:
            return jsonify({"status": "error", "message": "Failed to generate JWT token", "credits": "TEAM-AKIRU", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}), 500

        encrypted_data = encrypt_api(f"08{Encrypt_ID(player_id)}1007")
        data = bytes.fromhex(encrypted_data)

        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        headers = {
            'X-Unity-Version': '2018.4.11f1',
            'ReleaseVersion': 'OB48',
            'Content-Type': 'application/octet-stream',
            'X-GA': 'v1 1',
            'Authorization': f'Bearer {jwt_token.strip()}',
            'User-Agent': 'Dalvik/2.1.0 (Linux; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Host': 'client.ind.freefiremobile.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'Region': 'IND'
        }

        response = requests.post(url, headers=headers, data=data, verify=False)

        if response.status_code == 200:
            hex_response = binascii.hexlify(response.content).decode('utf-8')
            json_result = get_available_room(hex_response)
            parsed_data = json.loads(json_result)

            basic = parsed_data["1"]["data"]
            player_data = {
                "basic_info": {
                    "name": basic["3"]["data"],
                    "id": player_id,
                    "likes": basic["21"]["data"],
                    "level": basic["6"]["data"],
                    "server": basic["5"]["data"],
                    "bio": parsed_data["9"]["data"]["9"]["data"],
                    "booyah_pass_level": basic["18"]["data"],
                    "account_created": datetime.fromtimestamp(basic["44"]["data"]).strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            try:
                player_data["animal"] = {"name": parsed_data["8"]["data"]["2"]["data"]}
            except:
                player_data["animal"] = None

            try:
                guild = parsed_data["6"]["data"]
                leader = parsed_data["7"]["data"]
                player_data["Guild"] = {
                    "name": guild["2"]["data"],
                    "id": guild["1"]["data"],
                    "level": guild["4"]["data"],
                    "members_count": guild["6"]["data"],
                    "leader": {
                        "id": guild["3"]["data"],
                        "name": leader["3"]["data"],
                        "level": leader["6"]["data"],
                        "booyah_pass_level": leader["18"]["data"],
                        "likes": leader["21"]["data"],
                        "account_created": datetime.fromtimestamp(leader["44"]["data"]).strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            except:
                player_data["Guild"] = None

            return jsonify({
                "status": "success",
                "message": "Player information retrieved successfully",
                "data": player_data,
                "credits": "TEAM-AKIRU",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({
            "status": "error",
            "message": f"API request failed with status code: {response.status_code}",
            "credits": "TEAM-AKIRU",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), response.status_code

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "credits": "TEAM-AKIRU",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
