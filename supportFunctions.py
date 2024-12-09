import subprocess


class supportFNs:

    def get_ip_addresses(self):
        result = subprocess.run(['ip', 'addr'], stdout=subprocess.PIPE, text=True)
        ip_addresses = []
        for line in result.stdout.split('\n'):
            if 'inet ' in line and '127.0.0.1' not in line:
                ip_address = line.split()[1].split('/')[0]
                ip_addresses.append(ip_address)
        res = ', '.join(ip_addresses)
        return res
