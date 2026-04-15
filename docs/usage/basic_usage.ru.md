# Базовое использование

Это руководство описывает, как установить и использовать Genesis Core на существующей инфраструктуре. Существующая инфраструктура может быть локальной машиной или несколькими серверами.
Предполагается, что на ваших машинах используется Linux (Ubuntu).

## Требования

Перед установкой и использованием Genesis Core необходимо установить несколько зависимостей:

### Пакеты

Установите необходимые пакеты:

#### Ubuntu

Установка пакетов

```bash
sudo apt update
sudo apt install qemu-kvm qemu-utils libvirt-daemon-system libvirt-dev mkisofs -y
```

Добавьте пользователя в группы

```bash
sudo adduser $USER libvirt
sudo adduser $USER kvm
```

### Libvirt

Создайте пул хранения libvirt или используйте `default`, если он уже существует.

Проверьте пулы:

```bash
sudo virsh pool-list --all
```

Создайте новый пул, если ни один не существует, или если вы хотите использовать другой.

```bash
sudo virsh pool-define-as default dir --target "/var/lib/libvirt/images/"
sudo virsh pool-build default
sudo virsh pool-start default
sudo virsh pool-autostart default
```

Проверьте статус с помощью virsh-info:

```bash
sudo virsh pool-info default
```

## Установка

Самый простой способ установки Genesis Core — получить готовый образ виртуальной машины со всеми необходимыми зависимостями. Возьмите [последний образ здесь](http://repository.genesis-core.tech:8081/genesis-core/latest/genesis-core.qcow2).

### Локальная машина / Разработка

Сначала установите Genesis DevTools. Для получения дополнительной информации о нём см. [Genesis DevTools](https://github.com/infraguys/genesis_devtools). Этот инструмент позволяет собирать и запускать genesis core локально. Поскольку мы уже загрузили последний образ, нам не нужно собирать его с нуля, но если вам нужно собрать образ из исходников, смотрите [инструкции здесь](https://github.com/infraguys/genesis_devtools?tab=readme-ov-file#build).

У инструмента devtools есть команда `bootstrap`, которая запустит Genesis Core локально.

```bash
genesis bootstrap -i genesis-core.raw -m core
```

Для получения дополнительной информации о команде `bootstrap` см. [инструкции здесь](https://github.com/infraguys/genesis_devtools?tab=readme-ov-file#bootstrap).

Установка доступна по адресу `10.20.0.2`, но на данный момент она не очень полезна, так как не может запускать рабочие нагрузки. Давайте добавим локальную машину в качестве гипервизора, чтобы решить эту проблему.

#### Получение токена администратора

Прежде чем мы сможем добавить гипервизор, нам нужно получить токен администратора. Команда для получения токена:

```bash
curl --location 'http://10.20.0.2:11010/v1/iam/clients/00000000-0000-0000-0000-000000000000/actions/get_token/invoke' \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=password' \
    --data-urlencode 'username=<ВАШЕ_ADMIN_ИМЯ>' \
    --data-urlencode 'password=<ВАШ_ADMIN_ПАРОЛЬ>' \
    --data-urlencode 'client_id=GenesisCoreClientId' \
    --data-urlencode 'client_secret=GenesisCoreClientSecret' \
    --data-urlencode 'scope=' \
    --data-urlencode 'ttl=86400'
```

Возвращаемое значение — это `json` объект с полем `access_token`. Скопируйте токен и используйте его на следующих шагах.

#### Добавление гипервизора

##### Libvirt через SSH (предпочтительно)

Создайте ключ в виртуальной машине Genesis Core для пользователя root:

```console
# ssh-keygen
```

Скопируйте публичный ключ на гипервизор (рекомендуемый пользователь — `ubuntu`)

##### Libvirt через TCP соединение

Нам нужен доступ к libvirt через TCP-соединение. По умолчанию TCP-соединение закрыто, поэтому нам нужно его включить.

**ПРИМЕЧАНИЕ:** Для разработки мы можем использовать raw TCP-соединение. Не используйте его в production.

Отредактируйте конфигурационный файл libvirt `/etc/libvirt/libvirtd.conf`, добавьте эти строки:

```bash
listen_tcp = 1
listen_addr = "0.0.0.0"
auth_tcp = "none"
```

Выполните команды для включения TCP-соединения libvirt:

```bash
sudo systemctl stop libvirtd
sudo systemctl enable --now libvirtd-tcp.socket
sudo systemctl start libvirtd
```

Проверьте, что libvirt слушает TCP-сокет:

```bash
sudo systemctl status libvirtd.service
sudo systemctl status libvirtd.service | grep "libvirtd-tcp.socket"
```

##### Настройка ZFS для хранения

Рекомендуется создать отдельный датасет для zvols:

```bash
zpool create rpool ... # создаём сам пул
zfs create -o volmode=dev rpool/disks
virsh pool-define-as --name rpool --source-name rpool/disks --type zfs
virsh pool-start rpool
virsh pool-autostart rpool
```

##### Конфигурация гипервизора в core

Добавьте машину в качестве гипервизора, замените XXXX на токен из предыдущего шага:

```bash
curl --location --globoff 'http://10.20.0.2:11010/v1/compute/hypervisors/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer XXXX' \
--data '{
    "driver_spec": {
        "driver": "libvirt",
        "iface_mtu": 1500,
        "network_type": "network",
        "network": "genesis-core-net",
        "storage_pool": "default", // для qcow
        "storage_pool": "rpool", // для ZFS
        "connection_uri": "qemu+tcp://10.20.0.1/system", // для TCP-соединения
        "connection_uri": "qemu+ssh://ubuntu@10.20.0.1:22/system?no_verify=1", // для SSH-соединения
        "machine_prefix": "dev-"
    },
    "avail_cores": 4,
    "avail_ram": 4096,
    "all_cores": 4,
    "all_ram": 4096,
    "status": "ACTIVE"
}'
```

- storage_pool — имя пула хранения libvirt для использования.
- connection_uri — URI подключения libvirt. Если вам нужно добавить другую машину, используйте другой IP-адрес.
- all_cores — общее количество ядер, которые вы хотите выделить гипервизору.
- all_ram — общий объём RAM, который вы хотите выделить гипервизору.
- avail_cores — используйте то же значение, что и `all_cores`.
- avail_ram — используйте то же значение, что и `all_ram`.

### Production

Руководство по установке в production будет добавлено позже.

## Использование

Следуйте [руководству по использованию](https://github.com/infraguys/genesis_core/wiki/Usage) для получения дополнительной информации.
