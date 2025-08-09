# backend/utils.py
import hmac
import hashlib

def verify_telegram_init_data(init_data: str, bot_token: str) -> bool:
    # init_data: Telegram থেকে আসা initData string (key=value&key=value...)
    # bot_token: তোমার বটের টোকেন (string)

    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Telegram init_data থেকে signature আলাদা করতে হবে
    # signature key কে বাদ দিয়ে বাকি parts sorted করে canonical string বানাও
    data_params = dict(pair.split('=') for pair in init_data.split('&') if pair.startswith('hash')==False)
    sorted_items = sorted(data_params.items())
    data_check_string = '\n'.join(f"{k}={v}" for k,v in sorted_items)

    # HMAC SHA256 signature তৈরি করো
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # init_data এর hash value (signature)
    from urllib.parse import parse_qs
    qs = parse_qs(init_data)
    received_hash = qs.get('hash', [None])[0]

    # তুলনা করো
    return hmac_hash == received_hash
