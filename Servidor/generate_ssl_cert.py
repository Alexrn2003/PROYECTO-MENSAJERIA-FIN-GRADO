#!/usr/bin/env python3
"""
Script para generar certificados SSL/TLS autofirmados para EasyCom
Necesario para HTTPS en Windows Server

Uso:
    python generate_ssl_cert.py "easycom.local"
    
Esto generará:
    - cert.pem (certificado)
    - key.pem (clave privada)
"""

import os
import sys
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generar_certificado(domain_name="easycom.local"):
    """
    Genera un certificado SSL/TLS autofirmado.
    
    Args:
        domain_name: El nombre de dominio para el certificado (ej: easycom.local)
    """
    print(f"🔐 Generando certificado SSL/TLS autofirmado para: {domain_name}")
    
    # Generar clave privada
    print("   -> Generando clave privada RSA (2048 bits)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Generar certificado
    print("   -> Generando certificado autofirmado...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"ES"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Madrid"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Madrid"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"EasyCom Corp"),
        x509.NameAttribute(NameOID.COMMON_NAME, domain_name),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(domain_name),
            x509.DNSName(f"*.{domain_name}"),
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Guardar certificado
    cert_path = "cert.pem"
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"   ✓ Certificado guardado en: {cert_path}")
    
    # Guardar clave privada
    key_path = "key.pem"
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"   ✓ Clave privada guardada en: {key_path}")
    
    print("\n" + "="*60)
    print("✅ Certificado generado correctamente")
    print("="*60)
    print(f"Dominio: {domain_name}")
    print(f"Válido por: 365 días")
    print(f"Tipo: Autofirmado (para desarrollo/testing)")
    print("\n⚠️  IMPORTANTE:")
    print("   Este certificado es AUTOFIRMADO y solo es válido para desarrollo.")
    print("   Para PRODUCCIÓN, debes obtener un certificado de una CA confiable.")
    print("   Los navegadores mostrarán advertencia de seguridad.\n")
    print("El servidor iniciará con HTTPS cuando uses run_server.py\n")


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "easycom.local"
    
    # Verificar si ya existen certificados
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        print("⚠️  Ya existen certificados (cert.pem, key.pem)")
        respuesta = input("¿Deseas regenerarlos? (s/n): ").strip().lower()
        if respuesta != "s":
            print("Operación cancelada.")
            sys.exit(0)
    
    try:
        generar_certificado(domain)
    except ImportError:
        print("\n❌ Error: Se requiere la librería 'cryptography'")
        print("   Instálala con: pip install cryptography")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error al generar certificado: {e}")
        sys.exit(1)
