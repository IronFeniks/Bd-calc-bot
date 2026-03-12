import sys
import subprocess

def check_and_install():
    print("🔍 Проверка библиотек...")
    
    libs = [
        ('google_auth_oauthlib', 'google-auth-oauthlib==1.2.0'),
        ('google_auth_httplib2', 'google-auth-httplib2==0.2.0'),
        ('googleapiclient', 'google-api-python-client==2.120.0')
    ]
    
    for module_name, package in libs:
        try:
            __import__(module_name)
            print(f"✅ {module_name} установлен")
        except ImportError:
            print(f"❌ {module_name} НЕ установлен. Устанавливаю...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {module_name} установлен")

if __name__ == "__main__":
    check_and_install()
    print("\n📋 Финальная проверка:")
    try:
        from google_auth_oauthlib.flow import Flow
        print("✅ google-auth-oauthlib работает!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
