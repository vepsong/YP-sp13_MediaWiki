import json
from utils import load_and_check_env_vars, write_json_to_file, run_command

# Имена переменных, которые нужно загрузить
env_vars = ["REPO_PATH", "CREDENTIALS_DIR_ABSOLUTE_PATH", "TERRAFORM_ABSOLUTE_PATH"]

# Проверяем наличие переменных окружения и добавляем их в словарь
env_var_dic = load_and_check_env_vars(env_vars)


# Шаг 1. Получение данных ВМ, созданных через Terraform
def get_terraform_vm_data(terraform_folder_path):
    """Получение данных ВМ (имя, ip, ip-nat и пр.), созданных через Terraform"""
    command = ['terraform', 'output', '-json']
    output = run_command(command, cwd=terraform_folder_path, capture_output=True)
    data = json.loads(output)
    print(data)
    return data


if __name__ == '__main__':
    # Определение абсолютных путей к файлам и папкам
    file_name = "terraform_vm_data.json"
    terraform_vm_data_file_in_credentials = f'{env_var_dic["CREDENTIALS_DIR_ABSOLUTE_PATH"]}/{file_name}'
    terraform_folder_path = env_var_dic["TERRAFORM_ABSOLUTE_PATH"]

    # Получение данных и запись в новый файл JSON
    terraform_vm_data = get_terraform_vm_data(terraform_folder_path)
    write_json_to_file(terraform_vm_data, terraform_vm_data_file_in_credentials)
