import subprocess
import configparser

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
    
    @staticmethod
    def merge_configs(src, dst):
        src_config = configparser.ConfigParser()
        dst_config = configparser.ConfigParser()
    
        src_config.read(src)
        dst_config.read(dst)
    
        updated = False
    
        # Add or update keys from src to dst
        for section in src_config.sections():
            if not dst_config.has_section(section):
                dst_config.add_section(section)
                updated = True
            for key, value in src_config.items(section):
                if not dst_config.has_option(section, key):
                    dst_config.set(section, key, value)
                    updated = True
        
        # Remove keys from dst that are not in src
        for section in dst_config.sections():
            if not src_config.has_section(section):
                dst_config.remove_section(section)
                updated = True
            else:
                for key in dst_config.options(section):
                    if not src_config.has_option(section, key):
                        dst_config.remove_option(section, key)
                        updated = True
    
        if updated:
            with open(dst, 'w') as configfile:
                dst_config.write(configfile)
            print(f"Config file {dst} updated with changes from {src}")

