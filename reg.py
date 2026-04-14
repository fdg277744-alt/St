import re,random
def reg(cc):
    try:
        # معالجة تنسيقات مختلفة للبطاقات
        patterns = [
            r'(\d{16})[|/ ](\d{1,2})[|/ ](\d{2,4})[|/ ](\d{3,4})',
            r'(\d{15})[|/ ](\d{1,2})[|/ ](\d{2,4})[|/ ](\d{3,4})',
            r'(\d{16})[|/ ](\d{1,2})[|/ ](\d{2,4})',
            r'(\d{15})[|/ ](\d{1,2})[|/ ](\d{2,4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, cc)
            if match:
                card = match.group(1)
                month = match.group(2).zfill(2)
                year = match.group(3)
                if len(year) == 2:
                    year = '20' + year
                
                if len(match.groups()) >= 4:
                    cvv = match.group(4)
                else:
                    cvv = str(random.randint(0, 999)).zfill(3)
                
                return f"{card}|{month}|{year}|{cvv}"
        
        return None
    except:
        return None