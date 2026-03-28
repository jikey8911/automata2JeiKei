import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

try:
    from adaptadores.binance_adapter import BinanceAdapter
    adapter = BinanceAdapter()
    print("✅ BinanceAdapter instanciado con éxito.")
except TypeError as e:
    print(f"❌ Error de instanciación: {e}")
except Exception as e:
    print(f"❌ Otro error: {e}")
