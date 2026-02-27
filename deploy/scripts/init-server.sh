#!/bin/bash
set -e

echo "═══ Инициализация сервера DOD ═══"

# 1. Обновление системы
apt-get update && apt-get upgrade -y

# 2. Установка Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 3. Docker Compose
apt-get install -y docker-compose-plugin

# 4. Создание пользователя
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# 5. SSH ключи
mkdir -p /home/deploy/.ssh
# Добавить публичный ключ
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# 6. Firewall
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# 7. Fail2Ban
apt-get install -y fail2ban
systemctl enable fail2ban

# 8. Swap (если мало RAM)
if [ $(free -g | awk '/Mem:/{print $2}') -lt 4 ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# 9. Директория проекта
mkdir -p /opt/dod
chown deploy:deploy /opt/dod

# 10. Timezone
timedatectl set-timezone UTC

echo "═══ Сервер готов ═══"
echo "Затем:"
echo "  1. git clone <repo> /opt/dod"
echo "  2. cp .env.production /opt/dod/"
echo "  3. cd /opt/dod && docker compose -f docker-compose.prod.yml up -d"
