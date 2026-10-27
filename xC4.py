# xC4.py — MAHIR Packet Layer (Join → Msg → Exit → Ghost + Recruit Mode + Group Join)
import time, requests, json, urllib3, base64, datetime, re, socket, threading, random, os, sys, asyncio
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# KEYS
# ============================================================
Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
Iv  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

SAFE_COLORS = ["[FF0000]","[00FF00]","[0000FF]","[FFFF00]","[FF00FF]","[00FFFF]",
               "[FFFFFF]","[FFA500]","[FFC0CB]","[ADD8E6]","[90EE90]","[DC143C]",
               "[00CED1]","[9400D3]","[FF1493]","[7CFC00]","[FF4500]","[DAA520]",
               "[00BFFF]","[00FF7F]","[4682B4]","[1E90FF]"]

def ArA_CoLor():
    return random.choice(["32CD32","00BFFF","00FA9A","90EE90","FF4500","FF6347",
                          "FF69B4","FF8C00","FFD700","FFDAB9","F0F0F0","F0E68C",
                          "A9A9A9","D2691E","CD853F","BC8F8F","6A5ACD","483D8B",
                          "4682B4","9370DB","C71585","FFA07A"])

def random_badge():
    return random.choice(["902000306","1200000004","901000194","827001005",
                          "827001006","203000543","203000348","827001008","902000308"])

def xBunnEr():
    return int(random.choice(['902000016','902000306','902000305','902000065',
                              '902000192','902000334','902000179','902000308',
                              '902045009','902038023','902048018','902039014']))

# ============================================================
# AUTH TOKEN CREATORS
# ============================================================
def create_auth_token_chat(account_id, jwt_token, timestamp, key, iv):
    """CHAT server auth — packet type 6d19 (18-byte header)"""
    try:
        K = bytes.fromhex(key) if isinstance(key, str) else key
        V = bytes.fromhex(iv)  if isinstance(iv,  str) else iv
        jwt_bytes = jwt_token.encode('utf-8')
        ct = AES.new(K, AES.MODE_CBC, V).encrypt(pad(jwt_bytes, AES.block_size))
        header = (bytes.fromhex('6d19') +
                  int(account_id).to_bytes(8, 'big') +
                  int(timestamp).to_bytes(4, 'big') +
                  len(ct).to_bytes(4, 'big'))
        return (header + ct).hex()
    except Exception as e:
        print(f"❌ CHAT AUTH ERROR: {e}")
        return None

def create_auth_token_online(account_uid, token, kts, key, iv):
    """ONLINE server auth — returns HEX STRING"""
    try:
        K = bytes.fromhex(key) if isinstance(key, str) else key
        V = bytes.fromhex(iv)  if isinstance(iv,  str) else iv
        enc_token = AES.new(K, AES.MODE_CBC, V).encrypt(pad(token.encode("utf-8"), 16))
        opcode    = bytes.fromhex("830c")
        full_pkt  = (opcode +
                     int(account_uid).to_bytes(8, byteorder="big") +
                     int(kts).to_bytes(4, byteorder="big") +
                     len(enc_token).to_bytes(8, byteorder="big") +
                     enc_token)
        return full_pkt.hex()
    except Exception as e:
        print(f"❌ ONLINE AUTH ERROR: {e}")
        return None

# ============================================================
# ASYNC PROTOBUF HELPERS
# ============================================================
async def EnC_Vr(N):
    if N < 0: return b''
    H = []
    while True:
        b = N & 0x7F; N >>= 7
        if N: b |= 0x80
        H.append(b)
        if not N: break
    return bytes(H)

async def CrEaTe_VarianT(fn, val):
    return await EnC_Vr((fn << 3) | 0) + await EnC_Vr(val)

async def CrEaTe_LenGTh(fn, val):
    ev = val.encode() if isinstance(val, str) else val
    return await EnC_Vr((fn << 3) | 2) + await EnC_Vr(len(ev)) + ev

async def CrEaTe_ProTo(fields):
    packet = bytearray()
    for f, v in fields.items():
        if isinstance(f, str):
            try: f = int(f)
            except: continue
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    nested = await CrEaTe_ProTo(item)
                    packet.extend(await CrEaTe_LenGTh(f, nested))
        elif isinstance(v, dict):
            nested = await CrEaTe_ProTo(v)
            packet.extend(await CrEaTe_LenGTh(f, nested))
        elif isinstance(v, bool):
            packet.extend(await CrEaTe_VarianT(f, int(v)))
        elif isinstance(v, int):
            packet.extend(await CrEaTe_VarianT(f, v))
        elif isinstance(v, (str, bytes)):
            packet.extend(await CrEaTe_LenGTh(f, v))
    return bytes(packet)

async def DecodE_HeX(H):
    F = str(hex(H))[2:]
    return "0" + F if len(F) == 1 else F

async def EnC_PacKeT(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

async def GeneRaTePk(Pk, N, K, V):
    PkEnc = await EnC_PacKeT(Pk, K, V)
    _ = await DecodE_HeX(len(PkEnc) // 2)
    if   len(_) == 2: HeadEr = N + "000000"
    elif len(_) == 3: HeadEr = N + "00000"
    elif len(_) == 4: HeadEr = N + "0000"
    elif len(_) == 5: HeadEr = N + "000"
    else:             HeadEr = N + "0000"
    return bytes.fromhex(HeadEr + _ + PkEnc)

def Fix_PackEt(parsed_results):
    rd = {}
    for r in parsed_results:
        fd = {'wire_type': r.wire_type}
        if r.wire_type in ["varint","string","bytes"]: fd['data'] = r.data
        elif r.wire_type == 'length_delimited': fd["data"] = Fix_PackEt(r.data.results)
        rd[r.field] = fd
    return rd

def DeCode_PackEt(input_text):
    try: return json.dumps(Fix_PackEt(Parser().parse(input_text)))
    except Exception: return None

# ============================================================
# CHAT PACKETS
# ============================================================
async def yasser_Chat(uid, code, K, I):
    fields = {1: 3, 2: {1: int(uid), 3: "fr", 4: str(code)}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '1215', K, I)

async def yasser_quitcaht(uid, K, I):
    fields = {1: 4, 2: {1: int(uid), 3: "fr"}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '1215', K, I)

async def Msg_Packet(msg, owner, bot, K, I):
    fields = {
        1: 1,
        2: {
            1: int(bot), 2: int(owner), 4: msg,
            5: int(time.time()),
            9: {
                1: "Fun1w5a2", 2: xBunnEr(), 3: int(random_badge()), 4: 330,
                5: int(random_badge()), 10: 1, 11: 1, 7: 2,
                13: {1: 2},
                14: {1: int(bot), 2: 8,
                    3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"}
            },
            10: "fr", 13: {2: 1, 3: 1}, 14: {}
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '1215', K, I)

async def ChaT_sQ(T, N, U, sQ, K, V):
    fields = {1: N, 2: {1: int(U), 3: f"{T}", 4: str(sQ)}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '1215', K, V)

# ============================================================
# JOIN — RANDOM SQUAD (Join_Sq)
# ============================================================
async def Join_Sq(K, V):
    fields = {
        1: 69,
        2: {
            2: random.choice(['tr', 'en', 'ar', 'fr']),
            7: 330, 8: 330, 9: "",
            10: "\u0001\t\n\u000b\u0012\u0019 '",
            11: 1,
            12: {
                1: "088B823A900F2FEF020101000000000200140001001100020E682E6B13949B6B46762514110000010594e97dca3ca4f96a3ba7bd0000004f00000100cacfa16d",
                2: 31,
                3: "tY_S\u0013\b\u0001MV\u0003\u0007\u0005\u0004W\u0005]\u0007\t\u0002\u0007\u0001\u0000\u0003\u0000T\fS\u0006\u0000W\u0004\u0003\u0002\u0000\b\r\u0000\u0001U\u0005\u0011\u0001\u0002JuTAEN\u001e\u0002\u001c\u0002\u001f\u0013\b\u0003M\u001cDbz_Q@}p_QOgsC\u001dYVI\u0004UAAj_ga\u0004\u0012\u0000K\u001d\u0007_t\u0019b\bCx\u0002UeGat\u001fTTCBLER\u0006\u0001\r\f\u0012\u0006\u0005NYaeA~ha\u000fZzr\u0006IZw|F}qf\u007f\u0001l\u0007t\n\u0015\nL\\Nh\u0000~G\u000et\u0000eb]VQ\u0006t^F[ZIGxCdZD\u000b\u0011\u0002OA\u0000\u000fgTtbgJcfq\u0001euAYAQKQtTsHD{\u000f\u0013\nJx^k^EO[c\u0005aTRw\u0002\u007fw@\u007f\u0002BX\ntY@@]\r\u0010\u0007\bES~N[kxUE\u0002o\u001eZ\\C@A{F[tvhN\u0003Qr\u000b\u0013\nMr\u0018zTzK}\u007fqE]vnvwROuheYvwduvQ\r\u001a\u0005M\u0006z\u001dfXfzvHFc~dXUz}O\u001aB\u0005t\u0002i\u001co_\u0004\u0012\u0003\u0007J\u0006b\u0003\u000eqlfvbEstgu~wB\u0001v@yI\u0002ZPx\f\u0014\u0003NR\u0002yBZvuD_cd\u0004q]lH]\u0007bD}pCe\t\u0004t\n",
                4: "w^_R", 6: 11, 7: "\u0016xx`wc\u0015\u0013", 8: "1.128.15", 9: 3, 10: 2,
                11: "0003626253513637456372725663416456324b796f566c586c6449716f4662743755656f5a4c633547475052557472782f7646515a4c54753272754d7432676d6875504f4d6c5a74444371496c4c5944447961546572366864394e6774365462364e754549774959395243614f3348793873666b47696c6444656b36394846426e3657442b31415430695566336e42714b41724b38315945743231393671617a4e61434144514f6772466c6e614358306f646849436b35625347476963687a6e61764850757264562b5a4365576d4a6470736f556961504d544c3039587662345530674b6453486d4a396b2b56476767432f6d525972613965476c52444d4a4d45566b36434a4458786e6a6263327a7a4c536e32576a5a4977646f7a305750796368415a4970636f61366c6d35794474636c734c3953514c74615055617370626549314f6b5a5a3265517062786837774152464e617a4642795661354a79546e675558425a796246566565464f656a6b6d53585a714e5764567a65314443583858737a414364795246636332624e6a7438476e4866396d61744d492b766a33577a6446526c537073655350582f364945714157546c45306a6958785674656144586a2f6878716b49312b6339695534736f52666578526e757548486d4f33583839476277475678695475774278764772746532616732582f4f4f51497a44314d644177475177386e364b584c646c4f44547274654f7448306170324174674e6d4634694d6a654c484e4c70504c366964694e5850594633413d3d"
            },
            16: 1,
            17: "\u0001\u0002\u0003\u0004",
            18: "\u0001\u0002\u0003\u0004\u0005",
            21: "\b\u0015",
            28: "\bH\u0010\u0003",
            29: 5
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)

# ============================================================
# JOIN — BY RECRUIT CODE (async)
# ============================================================
async def Join_By_RecruitCode(owner_uid, recruit_code, K, V, region="bd"):
    """Join a specific squad via owner UID + recruit code."""
    try:
        fields = {
            1: 4,
            2: {
                1: int(owner_uid),
                3: int(owner_uid),
                8: 1,
                9: {2: 161, 4: "y[WW", 6: 11, 8: "1.126.7", 9: 3, 10: 1},
                10: str(recruit_code),
            }
        }
        if region.lower() == "ind":  p_type = '0514'
        elif region.lower() == "bd": p_type = '0519'
        else:                        p_type = '0515'
        return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), p_type, K, V)
    except Exception as e:
        print(f"❌ Join_By_RecruitCode error: {e}")
        return b""

# ============================================================
# 🎴 V-BADGE INVITE CARD (async)
# ============================================================
BADGE_VALUES = {'s2': 32768}

async def auto_s2_invite_async(target_uid, key, iv, region, writer):
    """
    V-Badge (Moderator) Invite Card → target-এর স্ক্রিনে বড় pop দেখাবে।
    writer = asyncio StreamWriter (online server)
    """
    try:
        real_uid = int(float(str(target_uid)))
        badge_value = BADGE_VALUES.get('s2', 32768)
        reg = (region or "bd").upper()

        fields = {
            1: 33,
            2: {
                1: real_uid,
                2: reg,
                3: 1, 4: 1,
                5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]),
                6: "iG:[C][B][FF0000] MAHIR",
                7: 330, 8: 1000,
                10: reg,
                12: 1, 13: real_uid,
                14: {1: 2203434355, 2: 8,
                    3: b"\x10\x15\x08\x0a\x0b\x13\x0c\x0f\x11\x04\x07\x02\x03\r\x0e\x12\x01\x05\x06"},
                16: 1, 17: 1, 18: 312, 19: 46,
                24: 902000306,
                31: {1: 1, 2: badge_value},
                32: badge_value,
            }
        }

        proto_data = await CrEaTe_ProTo(fields)

        rl = (region or "bd").lower()
        if rl == "bd":    p_type = '0519'
        elif rl == "ind": p_type = '0514'
        else:              p_type = '0515'

        final_packet = await GeneRaTePk(proto_data.hex(), p_type, key, iv)

        if writer is not None:
            writer.write(final_packet)
            await writer.drain()
        return True
    except Exception as e:
        print(f"❌ auto_s2_invite error: {e}")
        return False


# ============================================================
# 🎬 ANIMATION / BUNDLE
# ============================================================
AUTO_BUNDLE_POOL = [914000002, 914000003, 914038001, 914039001, 914042001,
                    914044001, 914047001, 914047002, 914048001, 914050001,
                    914051001, 914053001]
ANIMATION_POOL = AUTO_BUNDLE_POOL[:]
DEFAULT_JOIN_EMOTES = [909049013, 909045010, 909000020, 909000010,
                       909055004, 909055005, 909000062]


async def mahir_animation_packet_async(animation_id, key, iv):
    """Returns animation packet bytes → online_writer দিয়ে পাঠাতে হবে।"""
    try:
        fields = {1: 88, 2: {1: {1: int(animation_id)}}}
        packet_hex = (await CrEaTe_ProTo(fields)).hex()
        encrypted = await EnC_PacKeT(packet_hex, key, iv)
        pl = len(encrypted) // 2
        hl = format(pl, 'x')
        if len(hl) < 2:
            hl = "0" + hl
        return bytes.fromhex("051500" + "0" * (6 - len(hl)) + hl + encrypted)
    except Exception as e:
        print(f"animation err: {e}")
        return None


async def Mahir_bundle_packet_async(bundle_id, key, iv, region="bd"):
    """Returns bundle packet bytes → online_writer দিয়ে পাঠাতে হবে।"""
    try:
        fields = {1: 88, 2: {1: {1: bundle_id, 2: 1}, 2: 2}}
        encrypted = await EnC_PacKeT((await CrEaTe_ProTo(fields)).hex(), key, iv)
        hl = await DecodE_HeX(len(encrypted) // 2)
        rl = (region or "bd").lower()
        pt = '0514' if rl == "ind" else ('0519' if rl == "bd" else '0515')
        if   len(hl) == 2: fh = pt + "000000"
        elif len(hl) == 3: fh = pt + "00000"
        elif len(hl) == 4: fh = pt + "0000"
        elif len(hl) == 5: fh = pt + "000"
        else:               fh = pt + "000000"
        return bytes.fromhex(fh + hl + encrypted)
    except Exception as e:
        print(f"bundle err: {e}")
        return None


async def Mahir_bundle_packet_2_async(bundle_id, key, iv, region="bd"):
    """Returns bundle variant-2 packet bytes → online_writer দিয়ে পাঠাতে হবে।"""
    try:
        fields = {1: 88, 2: {1: {1: bundle_id, 2: 2}, 2: 2}}
        encrypted = await EnC_PacKeT((await CrEaTe_ProTo(fields)).hex(), key, iv)
        hl = await DecodE_HeX(len(encrypted) // 2)
        rl = (region or "bd").lower()
        pt = '0514' if rl == "ind" else ('0519' if rl == "bd" else '0515')
        if   len(hl) == 2: fh = pt + "000000"
        elif len(hl) == 3: fh = pt + "00000"
        elif len(hl) == 4: fh = pt + "0000"
        elif len(hl) == 5: fh = pt + "000"
        else:               fh = pt + "000000"
        return bytes.fromhex(fh + hl + encrypted)
    except Exception as e:
        print(f"bundle2 err: {e}")
        return None

async def Join_By_RecruitCode_Alt(owner_uid, recruit_code, K, V, region="bd"):
    """Alternative full join packet with device fingerprint (async)."""
    try:
        fields = {
            1: 4,
            2: {
                1: int(owner_uid),
                3: int(owner_uid),
                4: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000e\u0016\u0019\u001a \u001d'",
                5: str(recruit_code),
                6: 6,
                8: 1,
                9: {
                    2: 3140,
                    3: "vX\\Q\u0016\u0005\bN\u0006R\b\u0001U\u0002\rR[\u0003TU\u0006\b\u0007U\u0004P\\\u0000RRRT\t\u0007\fP\n\nS\u0000\u0013\u0000\u0001HpYHFN\u001e\u0000\u001d\u0001\u001d\u0016\u0005\nN[U\u0006\u0003cwewhaSdeF^Fr}Q|V\u000edRS\u0000\u0005\t\u001b\u0003K^s`c^\u0005\u001fw\u0003\u0005@Bz\u0006\u0006\\{\bVbSR~J{La\u0005\u0011\u0006\u0005L[UNAwHZ_\u0019s~_Rvdy\u001d_uq\u001aCNRpM{\n\u0015\bMaBR[JQezTvcELuu\u0005_tHdFS\u0006`OY\u0007\u000b\u0013\u0003LYA\u0000AAzPWdqDy~Uj\u007f\\\u0005\u007fGgovQzrU\r\u0012\tHq[@Dr[\u0000`zS|MIZR\u0005r\u0006g\u0005pM\nPTrS\f\u0013\u0005\rHIwVRhAgfl\u007f\u000e]R\u0019EZ\\A@\fLHYN\u001bXW\t\u0016\u0007DjydvuG\u0001]MU\u007fO\u0005^[tBcS\u0013J@\u0002\\ZJ\f\b\u0017\fNyNaV}F~\rT\u0006Y\u000fBzyag\u0007@{BxU^WNV\t\u001b\u0000\u0007J\\\u0003d\u0003vBBQ^^\u001bCd\u0005\\M`F@C\u007f\t\u0007^sUS\u000f\u0014\u0003LRX`lzm_\u0004ovtxDwPr@`^B_Y\\`Mks\n",
                    4: "zW\\R", 6: 11,
                    7: "\u0014twqqq~\u0016\u0013", 8: "1.120.19", 9: 3, 10: 2
                },
                13: "ar", 16: "7OR\u0019",
            }
        }
        if region.lower() == "ind":  p_type = '0514'
        elif region.lower() == "bd": p_type = '0519'
        else:                        p_type = '0515'
        return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), p_type, K, V)
    except Exception as e:
        print(f"❌ Join_By_RecruitCode_Alt error: {e}")
        return b""

# ============================================================
# 🎯 JOIN TARGET'S SQUAD (main.py style)
# ============================================================
async def Join_Group_Packet(target_uid, K, V):
    """Join a specific player's squad by their UID (BD/default, op 0515)."""
    fields = {
        1: 4,
        2: {
            1: int(target_uid),
            8: 1,
            9: {2: 161, 4: "y[WW", 6: 11, 8: "1.126.7", 9: 3, 10: 1},
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)


async def Join_CS_Packet(target_uid, K, V):
    """Join a specific player's squad (ID/CS variant, op 0514)."""
    fields = {
        1: 4,
        2: {
            1: int(target_uid),
            3: int(target_uid),
            8: 1,
            9: {2: 161, 4: "y[WW", 6: 11, 8: "1.126.7", 9: 3, 10: 1},
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0514', K, V)


async def Join_Squad_Packet_TC(squad_code, K, V):
    """Join a specific squad by squad_code (revenge flow)."""
    fields = {
        1: 4,
        2: {
            8: 1,
            9: {2: 161, 4: "y[WW", 6: 11, 8: "1.126.7", 9: 3, 10: 1},
            10: str(squad_code),
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)

# ============================================================
# JOIN_SQ1 / Send_GhosTs / Send_InV / yasser_SendInv
# ============================================================
async def Join_Sq1(T, U, rQ, K, V):
    fields = {
        1: 4,
        2: {
            1: U,
            4: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000f\u0019\u001a ",
            6: 1, 8: 1,
            9: {4: "y[WW", 6: 11, 7: "\u001d`at\u0005d\u001d\u0016",
                8: "1.118.3", 9: 3, 10: 2},
            13: "ar", 15: rQ, 16: "OR", 20: {1: 21}
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)


async def Send_GhosTs(Uid, Nm, sQ, K, V):
    fields = {
        1: 61,
        2: {
            1: int(Uid),
            2: {1: int(Uid), 2: 1159, 3: f'{Nm}', 5: 12, 6: 9999999,
                7: 1, 8: {2: 1, 3: 1}, 9: 3},
            3: sQ
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)


async def Send_InV(N, U, K, V):
    fields = {1: 2, 2: {1: int(U), 2: "ME", 4: N}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)


async def yasser_SendInv(bot_uid, uid, K, V):
    fields = {
        1: 33, 2: {
            1: int(uid), 2: "ME", 3: 1, 4: 1, 6: "yyt", 7: 330, 8: 1000, 9: 100,
            10: "DZ", 12: 1, 13: int(uid), 16: 1,
            17: {2: 159, 4: "y[WW", 6: 11, 8: "1.118.1", 9: 3, 10: 1},
            18: 306, 19: 18, 24: 902000306, 26: {},
            27: {1: 11, 2: int(bot_uid), 3: 999}, 28: {},
            31: {1: 1, 2: 32768}, 32: 32768,
            34: {1: bot_uid, 2: 8,
                 3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"}
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)

# ============================================================
# EXIT / GHOST / GLOBAL
# ============================================================
async def ExiT(K, V):
    fields = {1: 7, 2: {1: 0}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)


async def Ghost_Final_Packet(player_id, ghost_nm, secret_code, K, V):
    fields = {
        1: 61,
        2: {
            1: int(player_id),
            2: {
                1: int(player_id),
                2: 1159,
                3: f"[b][c][{ArA_CoLor()}]{ghost_nm}",
                5: 12,
                6: 9999999,
                7: 1,
                8: {2: 1, 3: 1},
                9: 3,
            },
            3: secret_code,
        }
    }
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), "0515", K, V)


async def GLobaL(T, K, V):
    fields = {1: 3, 2: {2: 5, 3: f"{T}"}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '1215', K, V)

# ============================================================
# SYNC VERSIONS (for CDX parity / external use)
# ============================================================
def encode_varint_sync(value):
    result = []
    if value < 0: value &= (1 << 64) - 1
    while True:
        byte = value & 0x7F; value >>= 7
        if value: byte |= 0x80
        result.append(byte)
        if not value: break
    return bytes(result)

def create_proto_sync(fields):
    packet = bytearray()
    for f, v in fields.items():
        if isinstance(v, dict):
            nested = create_proto_sync(v)
            packet.extend(encode_varint_sync((f << 3) | 2))
            packet.extend(encode_varint_sync(len(nested))); packet.extend(nested)
        elif isinstance(v, int):
            packet.extend(encode_varint_sync((f << 3) | 0)); packet.extend(encode_varint_sync(v))
        elif isinstance(v, str):
            enc = v.encode('utf-8')
            packet.extend(encode_varint_sync((f << 3) | 2))
            packet.extend(encode_varint_sync(len(enc))); packet.extend(enc)
        elif isinstance(v, bytes):
            packet.extend(encode_varint_sync((f << 3) | 2))
            packet.extend(encode_varint_sync(len(v))); packet.extend(v)
    return bytes(packet)

def generate_pk_sync(Pk, N, K, V):
    PkEnc = AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(Pk), 16)).hex()
    L = str(hex(len(PkEnc) // 2))[2:]
    if len(L) == 1: L = "0" + L
    if   len(L) == 2: HeadEr = N + "000000"
    elif len(L) == 3: HeadEr = N + "00000"
    elif len(L) == 4: HeadEr = N + "0000"
    elif len(L) == 5: HeadEr = N + "000"
    else:             HeadEr = N + "0000"
    return bytes.fromhex(HeadEr + L + PkEnc)


def Join_By_RecruitCodeSync(owner_uid, recruit_code, K, V, region="bd"):
    """Sync version — CDX.py parity."""
    try:
        fields = {
            1: 4,
            2: {
                1: int(owner_uid), 3: int(owner_uid), 8: 1,
                9: {2: 161, 4: "y[WW", 6: 11, 8: "1.126.7", 9: 3, 10: 1},
                10: str(recruit_code),
            }
        }
        if region.lower() == "ind":  p_type = '0514'
        elif region.lower() == "bd": p_type = '0519'
        else:                        p_type = '0515'
        return generate_pk_sync(create_proto_sync(fields).hex(), p_type, K, V)
    except Exception as e:
        print(f"❌ Join_By_RecruitCodeSync: {e}")
        return b""


def Join_By_RecruitCode_AltSync(owner_uid, recruit_code, K, V, region="bd"):
    try:
        fields = {
            1: 4,
            2: {
                1: int(owner_uid), 3: int(owner_uid),
                4: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000e\u0016\u0019\u001a \u001d'",
                5: str(recruit_code), 6: 6, 8: 1,
                9: {
                    2: 3140,
                    3: "vX\\Q\u0016\u0005\bN\u0006R\b\u0001U\u0002\rR[\u0003TU\u0006\b\u0007U\u0004P\\\u0000RRRT\t\u0007\fP\n\nS\u0000\u0013\u0000\u0001HpYHFN\u001e\u0000\u001d\u0001\u001d\u0016\u0005\nN[U\u0006\u0003cwewhaSdeF^Fr}Q|V\u000edRS\u0000\u0005\t\u001b\u0003K^s`c^\u0005\u001fw\u0003\u0005@Bz\u0006\u0006\\{\bVbSR~J{La\u0005\u0011\u0006\u0005L[UNAwHZ_\u0019s~_Rvdy\u001d_uq\u001aCNRpM{\n\u0015\bMaBR[JQezTvcELuu\u0005_tHdFS\u0006`OY\u0007\u000b\u0013\u0003LYA\u0000AAzPWdqDy~Uj\u007f\\\u0005\u007fGgovQzrU\r\u0012\tHq[@Dr[\u0000`zS|MIZR\u0005r\u0006g\u0005pM\nPTrS\f\u0013\u0005\rHIwVRhAgfl\u007f\u000e]R\u0019EZ\\A@\fLHYN\u001bXW\t\u0016\u0007DjydvuG\u0001]MU\u007fO\u0005^[tBcS\u0013J@\u0002\\ZJ\f\b\u0017\fNyNaV}F~\rT\u0006Y\u000fBzyag\u0007@{BxU^WNV\t\u001b\u0000\u0007J\\\u0003d\u0003vBBQ^^\u001bCd\u0005\\M`F@C\u007f\t\u0007^sUS\u000f\u0014\u0003LRX`lzm_\u0004ovtxDwPr@`^B_Y\\`Mks\n",
                    4: "zW\\R", 6: 11,
                    7: "\u0014twqqq~\u0016\u0013", 8: "1.120.19", 9: 3, 10: 2,
                },
                13: "ar", 16: "7OR\u0019",
            }
        }
        if region.lower() == "ind":  p_type = '0514'
        elif region.lower() == "bd": p_type = '0519'
        else:                        p_type = '0515'
        return generate_pk_sync(create_proto_sync(fields).hex(), p_type, K, V)
    except Exception as e:
        print(f"❌ Join_By_RecruitCode_AltSync: {e}")
        return b""

# ============================================================
# CRAFTLAND SHARE (sync)
# ============================================================
def send_craftland_share_sync(sock, bot_uid, target_id, chat_type, map_code, K, V):
    try:
        craftland_json = json.dumps({"WorkshopCode": map_code, "type": "UGCMapShare"})
        fields = {
            1: 1,
            2: {1: int(bot_uid), 2: int(target_id) if target_id else 0,
                3: int(chat_type) if chat_type is not None else 0,
                5: int(time.time()), 7: 1, 8: craftland_json,
                9: {1: "MAHIR BOT", 2: xBunnEr(), 4: 330, 5: 801046518,
                    8: "MAHIR TEAM", 10: 1, 11: 1, 13: {1: 2},
                    14: {1: 1158053040, 2: 8,
                         3: b"\x10\x15\x08\x0a\x0b\x15\x0c\x0f\x11\x04\x07\x02\x03\x0d\x0e\x12\x01\x05\x06"}},
                10: "en", 13: {2: 2, 3: 1}}
        }
        packet = generate_pk_sync(create_proto_sync(fields).hex(), '1215', K, V)
        if sock is not None:
            sock.send(packet)
        return True
    except Exception as e:
        print(f"❌ Craftland: {e}")
        return False