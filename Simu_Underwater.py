import sonar_simu
import config

if __name__ == '__main__':print('水下节点仿真')

def main():
    _sonar = sonar_simu.Sonar()        # Sonar实例化
    if config.configIns.data.sonar:
        if not _sonar.init():
            return False

main()