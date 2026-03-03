import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from logger import logger

# 学校相关的常量配置
SCHOOL_CONFIG = {
    "BASE_URL": "https://jw.hnit.edu.cn/njwhd",
    "LOGIN_URL": "https://jw.hnit.edu.cn/njwhd/login",
    "AES_KEY_HEX": "717a6b6a316b6a6768643d383736262a"  # 这是一个公开的硬编码密钥
}

def encrypt_password(password: str) -> str:
    """
    对密码进行加密处理（AES ECB + Double Base64）
    :param password: 原始密码
    :return: 加密后的字符串，若失败返回空字符串
    """
    try:
        # 1. 密钥处理：Hex转Bytes
        key_bytes = bytes.fromhex(SCHOOL_CONFIG["AES_KEY_HEX"])
        
        # 2. 密码预处理：前后加双引号
        payload = f'"{password}"'.encode('utf-8')
        
        # 3. AES加密 (ECB模式, PKCS7填充)
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        encrypted_bytes = cipher.encrypt(pad(payload, AES.block_size))
        
        # 4. 双重Base64编码
        first_b64 = base64.b64encode(encrypted_bytes)
        second_b64 = base64.b64encode(first_b64).decode('utf-8')
        
        return second_b64
    except Exception as e:
        logger.exception("密码加密失败")
        return ""
