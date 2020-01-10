/* Copyright 2001-2004 The Apache Software Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Cipher definitions
 */
typedef struct
{
    const char *name;            /* The mod_nss cipher name */
    PRInt32 num;                 /* The cipher id */
    const char *openssl_name;    /* The OpenSSL cipher name */
    PRInt32 attr;                /* cipher attributes: algorithms, etc */
    PRInt32 version;             /* protocol version valid for this cipher */
    PRInt32 strength;            /* LOW, MEDIUM, HIGH */
    PRInt32 bits;                /* bits of strength */
    PRInt32 alg_bits;            /* bits of the algorithm */
} cipher_properties;

/* OpenSSL-compatible cipher attributes */
#define SSL_kRSA  0x00000001L
#define SSL_aRSA  0x00000002L
#define SSL_aDSS  0x00000004L
#define SSL_DSS   SSL_aDSS
#define SSL_eNULL 0x00000008L
#define SSL_DES   0x00000010L
#define SSL_3DES  0x00000020L
#define SSL_RC4   0x00000040L
#define SSL_RC2   0x00000080L
#define SSL_MD5   0x00000200L
#define SSL_SHA1  0x00000400L
#define SSL_SHA   SSL_SHA1
#define SSL_RSA   (SSL_kRSA|SSL_aRSA)
#define SSL_kEDH  0x00000800L
#define SSL_EDH   (SSL_kEDH)
#define SSL_aNULL 0x00001000L
#define SSL_kECDHe 0x00002000L
#define SSL_aECDH 0x00004000L
#define SSL_aECDSA 0x00008000L
#define SSL_kECDHr 0x00010000L
#define SSL_kEECDH 0x00020000L

/* cipher strength */
#define SSL_STRONG_NONE   0x00000001L
#define SSL_NULL          0x00000002L
#define SSL_EXPORT40      0x00000004L
#define SSL_EXPORT56      0x00000008L
#define SSL_LOW           0x00000010L
#define SSL_MEDIUM        0x00000020L
#define SSL_HIGH          0x00000040L

#define SSL_AES128        0x00004000L
#define SSL_AES256        0x00008000L
#define SSL_CAMELLIA128   0x00010000L
#define SSL_CAMELLIA256   0x00020000L
#define SSL_AES128GCM     0x00040000L
#define SSL_AES256GCM     0x00080000L
#define SSL_SHA256        0x00100000L
#define SSL_AEAD          0x00200000L

#define SSL_AES           (SSL_AES128|SSL_AES256|SSL_AES128GCM|SSL_AES256GCM)
#define SSL_CAMELLIA      (SSL_CAMELLIA128|SSL_CAMELLIA256)

/* Protocols */
#define SSLV2              0x00000001L
#define SSLV3              0x00000002L
#define TLSV1              SSLV3
#define TLSV1_2            0x00000004L

/* the table itself is defined in nss_engine_cipher.c */
#ifdef NSS_ENABLE_ECC
#define ciphernum 49
#else
#define ciphernum 20
#endif

/* function prototypes */
int nss_parse_ciphers(server_rec *s, char *ciphers, PRBool cipher_list[ciphernum]);
int countciphers(PRBool cipher_state[ciphernum], int version);
