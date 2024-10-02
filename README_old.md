# Запуск корпоративного сервиса ведения документации с помощью MediaWiki
Яндекс Практикум | Курс "Системный Администратор" | Спринт-13  

## 1. Технические требования к проекту

1. ОС сервисов проекта: Ubuntu 22.04
2. Необходимые библиотеки и фреймворки:
    1. MediaWiki (php)
    2. PostgreSQL — для хранения данных MediaWiki
    3. pg_dump — для регулярного резервного копирования базы данных
3. Планируемая нагрузка (количество клиентов): 40
4. Интерфейс взаимодействия с пользователем (HTTP-сервис): веб-интерфейс MediaWiki
5. Вспомогательные сервисы:
    1. Nginx — для балансировки нагрузки и обработки HTTP-запросов
    2. Zabbix — для мониторинга состояния сервиса и инфраструктуры
    3. Ansible — для автоматизации настройки серверов и управления конфигурацией инфраструктуры
    4. Terraform — для автоматизированного создания и управления ВМ (серверами)
    5. Python — для автоматизации рутинных процессов

## 2. Задачи

1. [Создание схемы развертываемого приложения "Cервиса ведения документации на движке MediaWiki"](Solution/2.1.%20App%20deployment%20schema.md "App deployment schema").  
Обзор различных вариантов схем, оценка плюсов и минусов

    #### Вариант 1 (базовый)
    
    <details>
    <summary>Развернуть</summary>   

    ##### Компоненты:
    1. VM-1 - Сервисная VM. Точка входа администратора, деплой, управление, проксирование запросов и мониторинг состояния приложения, запуск Python-скриптов.
        - Стек технологий: Ubuntu 22.04, proxy-Nginx, Zabbix-Server, Teraform, Ansible, Python-скрипты
        - [**Zabbix-server**](https://www.zabbix.com/documentation/current/en// "Zabbix-server используется для настройки мониторинга состояния работы приложения"). Мониторинг состояния приложения.
        - [**Teraform**](https://developer.hashicorp.com/terraform/docs "Teraform используется для автоматизированного развертывания виртуальных машин и пр. элементов сетевой инфраструктуры"). Автоматический деплой ВМ
        - [**Ansible**](https://docs.ansible.com/ "Ansible используется для автоматической настройки виртуальных машин и пр. элементов сетевой инфраструктуры"). Автоматическая конфигурация ВМ.
        - proxy-[**Nginx**](https://nginx.org/en/). HTTP-запросы пользователей перенаправляются на один из серверов MediaWiki (VM-2,3,4)
            - Вид proxy: обратный — HTTP-запросы пользователей перенаправляются на один из серверов MediaWiki (VM-2,3,4)
            - Метод балансировки: <a href="#" title="Каждый сервер в равной степени поочередно обрабатывает запрос)">Round Robin</a> без веса. 
    2. VM-2, 3, 4 - серверы MediaWiki
        - Стек технологий: Ubuntu 22.04, [MediaWiki](https://www.mediawiki.org/wiki/Documentation "движок для создания wiki-проектов (типа Википедии)")
    3. VM-5 - Primary PostgreSQL
        - Стек технологий: Ubuntu 22.04, [PostgreSQL](https://www.postgresql.org/), Streaming Replication
        - Обработка read/write запросов от серверов MediaWiki (VM-2, VM-3, VM-4)
        - Асинхронный Streaming Replication на Standby PostgreSQL (VM-6)
    4. VM-6 - Standby PostgreSQL
        - Стек технологий: Ubuntu 22.04, [PostgreSQL](https://www.postgresql.org/), Streaming Replication
        - Получение и поддержание реплики данных от Primary PostgreSQL (VM-5)
        - Регулярное создание дампов базы данных (pg_dump) на внешний жесткий диск (HDD-1)
    5. HDD-1 - PostgreSQL_dump
        - Хранение pg_dump, создаваемых на Standby PostgreSQL (VM-6)

    ##### Плюсы/минусы:
    - Плюсы:
        - Постоянный мониторинг состояния компонентов приложения
            - Zabbix-сервер проверяет состояние компонентов приложения и отправляет уведомления системному администратору
        - Отказоустойчивость серверов MediaWiki (VM-2, 3, 4)
            - В случае аварии на одном из серверов MediaWiki, обратный proxy-Nginx (VM-1) перенаправит запрос на доступный сервер. 
        - Отказоустойчивость БД
            - В случае аварии на Primary PostgreSQL (VM-5), системный администратор получает уведомление от Zabbix-server'а и переведет Standby PostgreSQL (VM-6) в режим работы Primary
        - Сохранность данных в БД
            - Полная актуальная копия Primary PostgreSQL (VM-5) с небольшой задержкой хранится на Standby PostgreSQL (VM-6) (задержка обусловлена асинхронным асинхронным Streaming Replication)
            - Регулярные резервные копии Standby PostgreSQL (VM-6), хранящиеся на внешнем жестком диске (HDD-1)
        - Сохранность структуры БД
            - Внешний жесткий диск (HDD-1) хранит несколько резервных копий Standby PostgreSQL (VM-6), что позволяет восстановить БД до определенной точки во времени в случае повреждения структуры на Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6).

    - Минусы:
        - Авария на VM-1 - потенциальная точка отказа приложения (бутылочное горлышко)
            - Остановка proxy-Nginx приведет к недоступности для пользователей серверов MediaWiki (VM-2, 3, 4)
            - Остановка Zabbix-server'а остановит информирование системного администратора о состоянии работы приложения и лишит аналитики для оперативного ремонта
            - Возможное решение:
                - Дублирование функций VM-1
                    - Создание дополнительной VM с аналогичным стеком и настройками
                    - Настройка [**Keepalived**](https://keepalived.readthedocs.io/en/latest/ "Keepalived отслеживает состояние таргетных ВМ, и в случае необходимости, перенаправляет трафик на резерный cервер") на VM-1 и дублирующей VM для автоматического перенаправления трафика в случае аварии
        - Вероятность потери небольшой части последних записанных данных
            - Асинхронная репликация между Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6) может причиной потери части данных в случае аварии на Primary PostgreSQL (VM-5)
            - Возможное решение:
                - Использование синхронной репликации данных между Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6)  
                    - Данное решение способно замедлить общую скорость работы приложения.  
                    Стоит прибегать только в случае если критична потеря даже небольшого фрагмента последних записанных данных
        - Отсутствие автоматизированного алгоритма переключения ролей БД в случае аварии
            - Ручная процедура переключения Standby PostgreSQL (VM-6) в режим Primary, в случае аварии на Primary PostgreSQL (VM-5)
            - Ручная перенастройка серверов MediaWiki (VM-2, 3, 4) на работу с новой Primary БД
            - Возможное решение:
                - Настройка автоматического переключения режимов работы БД, настройка proxy для запросов серверов MediaWiki (VM-2, 3, 4) к БД
                    - Настройка [**Patroni**](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии") на Primary (VM-5) и Standby PostgreSQL (VM-6) для автоматического переключения режимов работы БД (Patroni auto-failover)
                    - Настройка [**ZooKeeper**](https://zookeeper.apache.org/doc/r3.9.2/index.html "ZooKeeper отслеживает текущее состояние БД и координирует Patroni") на VM-1 для активации Patroni auto-failover
                    - Настройка [**HAProxy**](https://www.haproxy.org/ "Haproxy балансирует нагрузку между БД и автоматически перенаправляет трафик") на VM-1 для проксирования от серверов MediaWiki (VM-2, VM-3, VM-4) к БД
        - Повышенная нагрузка на Primary PostgreSQL (VM-5)
            - Все запросы от серверов MediaWiki (VM-2, 3, 4) обрабатывает Primary PostgreSQL (VM-5), что может стать причиной медленной работы сервиса
            - Возможное решение:
                - Настройка [**HAProxy**](https://www.haproxy.org/ "Haproxy балансирует нагрузку между БД и автоматически перенаправляет трафик") на VM-1 для проксирования от серверов MediaWiki (VM-2, VM-3, VM-4) к БД
                - Настройка Standby PostgreSQL (VM-6) в режим работы "read" для помощи Primary PostgreSQL (VM-5) в обработке части запросов
                - Добавление отдельного медиасервера для обработки медиафайлов

    ![Схема развертываемого приложения](/Solution/Mediafiles/2.1.%20App_deployment_schema_files/1.2.%20MediaWiki_app_schema.svg)   

    [Ссылка на .drawio-файл](/Solution/Mediafiles/2.1.%20App_deployment_schema_files/1.1.%20MediaWiki_app_schema.drawio)   

    </details> 

    #### Вариант N2 (базовый+)

    <details>
    <summary>Развернуть</summary>

    ##### Компоненты:
    1. VM-1, VM-2 - Сервисные VM. Точка входа администратора, деплой, управление, проксирование запросов и мониторинг состояния приложения, запуск Python-скриптов.
        - Стек технологий: Ubuntu 22.04, proxy-Nginx, Zabbix-Server, Teraform, Ansible, Keepalived, ZooKeeper, HAProxy, Python-скрипты
        - [**Zabbix-server**](https://www.zabbix.com/documentation/current/en// "Zabbix-server используется для настройки мониторинга состояния работы приложения"). Мониторинг состояния приложения.
        - [**Teraform**](https://developer.hashicorp.com/terraform/docs "Teraform используется для автоматизированного развертывания виртуальных машин и пр. элементов сетевой инфраструктуры"). Автоматический деплой ВМ
        - [**Ansible**](https://docs.ansible.com/ "Ansible используется для автоматической настройки виртуальных машин и пр. элементов сетевой инфраструктуры"). Автоматическая конфигурация ВМ.
        - proxy-[**Nginx**](https://nginx.org/en/). HTTP-запросы пользователей перенаправляются на один из серверов MediaWiki (VM-2,3,4)
            - Вид proxy: обратный — HTTP-запросы пользователей перенаправляются на один из серверов MediaWiki (VM-2,3,4)
            - Метод балансировки: <a href="#" title="Каждый сервер в равной степени поочередно обрабатывает запрос)">Round Robin</a> без веса. 
        - [**Keepalived**](https://keepalived.readthedocs.io/en/latest/ "Keepalived отслеживает состояние таргетных ВМ, и в случае необходимости, перенаправляет трафик на резерный cервер"). Мониторинг состояния VM. И перенаправление трафика на резерную VM, в случае аварии. Используется для дублирования функций Nginx
        - [**ZooKeeper**](https://zookeeper.apache.org/doc/r3.9.2/index.html "ZooKeeper отслеживает текущее состояние БД и координирует Patroni"). Управление Patroni auto-failover, установленного на Primary PostgreSQL (VM-6) и Standby PostgreSQL (VM-7)
        - [**HAProxy**](https://www.haproxy.org/ "Haproxy балансирует нагрузку между БД и автоматически перенаправляет трафик"). Проксирование запросов от серверов MediaWiki (VM-3, VM-4, VM-5) к одной из БД
            - Метод балансировки: без веса
                - Primary PostgreSQL (VM-6) - read/write
                - Standby PostgreSQL (VM-7) - read
    2. VM-3, 4, 5 - серверы MediaWiki
        - Стек технологий: Ubuntu 22.04, [MediaWiki](https://www.mediawiki.org/wiki/Documentation "движок для создания wiki-проектов (типа Википедии)")
    3. VM-6 - Primary PostgreSQL
        - Стек технологий: Ubuntu 22.04, [PostgreSQL](https://www.postgresql.org/), Streaming Replication, Patroni
        - Обработка read/write запросов от серверов MediaWiki (VM-3, VM-4, VM-5)
        - Асинхронный Streaming Replication на Standby PostgreSQL (VM-6)
        - [**Patroni**](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии"). Автоматическая смена ролей Primary/StanBy, в случае аварии (Patroni auto-failover)
    4. VM-7 - Standby PostgreSQL
        - Стек технологий: Ubuntu 22.04, [PostgreSQL](https://www.postgresql.org/), Streaming Replication, Patroni
        - Обработка read запросов от серверов MediaWiki (VM-3, VM-4, VM-5)
        - Получение и поддержание реплики данных от Primary PostgreSQL (VM-6)
        - Регулярное создание дампов базы данных (pg_dump) на внешний жесткий диск (HDD-1)
        - [**Patroni**](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии"). Автоматическая смена ролей Primary/StanBy, в случае аварии (Patroni auto-failover)
    5. HDD-1 - PostgreSQL_dump
        - Хранение pg_dump, создаваемых на Standby PostgreSQL (VM-7)

    ##### Плюсы/минусы:

    - Плюсы:
        - Zabbix-сервер проверяет состояние компонентов приложения и отправляет уведомления системному администратору 
        - Отказоустойчивость серверов MediaWiki (VM-3, 4, 5)
            - В случае аварии на одном из серверов MediaWiki, обратный proxy-Nginx (VM-1, 2) перенаправит запрос на доступный сервер. 
        - Отказоустойчивость БД
            - В случае аварии на Primary PostgreSQL (VM-5), произойдет автоматическое переключение режима Standby PostgreSQL (VM-6) на Primary
        - Сохранность данных в БД
            - Полная актуальная копия Primary PostgreSQL (VM-6) с небольшой задержкой хранится на Standby PostgreSQL (VM-7) (задержка обусловлена асинхронным асинхронным Streaming Replication)
            - Регулярные резервные копии Standby PostgreSQL (VM-7), хранящиеся на внешнем жестком диске (HDD-1)
        - Сохранность структуры БД
            - Внешний жесткий диск (HDD-1) хранит несколько резервных копий Standby PostgreSQL (VM-7), что позволяет восстановить БД до определенной точки во времени в случае повреждения структуры на Primary PostgreSQL (VM-6) и Standby PostgreSQL (VM-7)

    - Минусы:
        - Большой объём задействованных ресурсов
            - Предложенный вариант содержит большое колчество VM, что увеличивает расходы на поддержание инфраструктуры
        - Простой резерной ВМ при штатном режиме работы приложения
            - VM-2 дублирует функции VM-1 и не принимает участие в работе приложения до момента возникновения аварии
            - Возможное решение:
                - Настройка Nginx для балансировки запросов между VM-1 и VM-2, для равномерного распределения нагрузки
        - Вероятность потери небольшой части последних записанных данных
            - Асинхронная репликация между Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6) может причиной потери части данных в случае аварии на Primary PostgreSQL (VM-5)
            - Возможное решение:
                - Использование синхронной репликации данных между Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6)  
                    - Данное решение способно замедлить общую скорость работы приложения.  
                    Стоит прибегать только в случае если критична потеря даже небольшого фрагмента последних записанных данных
        - Отсутствие специализированного механизма работы с медиафайлами
            - Крупные медиафайлы могут замедлить работу приложения
            - Возможное решение:
                - Добавление отдельного медиасервера для обработки медиафайлов

    ![Схема развертываемого приложения](/Solution/Mediafiles/2.1.%20App_deployment_schema_files/2.2.%20MediaWiki_app_schema.svg)   

    [Ссылка на .drawio-файл](/Solution/Mediafiles/2.1.%20App_deployment_schema_files/2.1.%20MediaWiki_app_schema.drawio)   

    </details> 
  

    #### Вариант N3 (компромиссный)

    <details>
    <summary>Развернуть</summary>

    ##### Компоненты:
    1. VM-1 - Сервисная VM. Точка входа администратора, деплой, управление,запуск Python-скриптов.
        - Стек технологий: Alpine Linux, Docker, GitHub, Teraform, Ansible, Python-скрипты
        - [**Alpine Linux**](https://www.alpinelinux.org/ "Официальный сайт Alpine Linux"). Легковесный дистрибутив Linux для быстрого развёртывания готовой сервисной VM
        - [**Docker**](https://www.docker.com/). Сборка образа из заранее подготовленного Dokcker file и дальнейший запуск VM в контейнере.
        - [**GitHub**](https://github.com/). Система контроля версий. Репозиторий для хранения конфигураций
        - [**Teraform**](https://developer.hashicorp.com/terraform/docs "Teraform используется для автоматизированного развертывания виртуальных машин и пр. элементов сетевой инфраструктуры"). Автоматический деплой ВМ
        - [**Ansible**](https://docs.ansible.com/ "Ansible используется для автоматической настройки виртуальных машин и пр. элементов сетевой инфраструктуры"). Автоматическая конфигурация ВМ.


    2. VM-2, VM-3 - Проксирование запросов и мониторинг состояния приложения.
        - Стек технологий: Ubuntu 22.04, proxy-Nginx, Zabbix-Server, Keepalived, ZooKeeper, HAProxy
        - [**Zabbix-server**](https://www.zabbix.com/documentation/current/en// "Zabbix-server используется для настройки мониторинга состояния работы приложения"). Мониторинг состояния приложения.

        - proxy-[**Nginx**](https://nginx.org/en/). HTTP-запросы пользователей сначала проксируются между VM-2 и VM-3 (т.е. nginx может оставить запрос на текущей VM или передать дублирующей) и далее перенаправляются на один из серверов MediaWiki (VM-4,5,6)
            - Балансировка между VM-2 и VM-3
                - Вид proxy: обратный — HTTP-запросы пользователей остаются либо на текущей VM, либо проксируются на дублирующую
                - Метод балансировки: <a href="#" title="Каждый сервер в равной степени поочередно обрабатывает запрос)">Round Robin</a> без веса. 
            - Балансировка между (VM-2 или VM-3) и серверами MediaWiki
                - Вид proxy: обратный — HTTP-запросы пользователей перенаправляются на один из серверов MediaWiki (VM-4,5,6)
                - Метод балансировки: <a href="#" title="Каждый сервер в равной степени поочередно обрабатывает запрос)">Round Robin</a> с весом: 70% (VM-4), 15% (VM-5), 15% (VM-6)
        - [**Keepalived**](https://keepalived.readthedocs.io/en/latest/ "Keepalived отслеживает состояние таргетных ВМ, и в случае необходимости, перенаправляет трафик на резерный cервер"). Мониторинг состояния VM. И перенаправление трафика на резерную VM, в случае аварии. Используется для дублирования функций Nginx
        - [**ZooKeeper**](https://zookeeper.apache.org/doc/r3.9.2/index.html "ZooKeeper отслеживает текущее состояние БД и координирует Patroni"). Управление Patroni auto-failover, установленного на Primary PostgreSQL (VM-7) и Standby PostgreSQL (VM-8)
        - [**HAProxy**](https://www.haproxy.org/ "Haproxy балансирует нагрузку между БД и автоматически перенаправляет трафик"). Проксирование запросов от серверов MediaWiki (VM-4,5,6) к одной из БД
            - Метод балансировки: без веса
                - Primary PostgreSQL (VM-5) - read/write
                - Standby PostgreSQL (VM-6) - read


    3. VM-4 - сервер MediaWiki
        - Стек технологий: Ubuntu 22.04, [MediaWiki](https://www.mediawiki.org/wiki/Documentation "движок для создания wiki-проектов (типа Википедии)")

    4. VM-5 - сервер MediaWiki, Primary PostgreSQL
        - Стек технологий: Ubuntu 22.04, [MediaWiki](https://www.mediawiki.org/wiki/Documentation "движок для создания wiki-проектов (типа Википедии)"), [PostgreSQL](https://www.postgresql.org/), Streaming Replication, [Patroni](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии")
        - Обработка read/write запросов от серверов MediaWiki (VM-4,5,6)
        - Асинхронный Streaming Replication на Standby PostgreSQL (VM-6)
        - [**Patroni**](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии"). Автоматическая смена ролей Primary/StanBy, в случае аварии (Patroni auto-failover)

    5. VM-6 - сервер MediaWiki, Standby PostgreSQL
        - Стек технологий: Ubuntu 22.04, [MediaWiki](https://www.mediawiki.org/wiki/Documentation "движок для создания wiki-проектов (типа Википедии)"), [PostgreSQL](https://www.postgresql.org/), Streaming Replication, [Patroni](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии")
        - Обработка read запросов от серверов MediaWiki (VM-4,5,6)
        - Получение и поддержание реплики данных от Primary PostgreSQL (VM-5)
        - Регулярное создание дампов базы данных (pg_dump) на внешний жесткий диск (HDD-1)
        - [**Patroni**](https://patroni.readthedocs.io/en/latest/README.html "Patroni осуществляет auto-failover Standby_db в режим Primary, в случае аварии"). Автоматическая смена ролей Primary/StanBy, в случае аварии (Patroni auto-failover)
    6. HDD-1 - PostgreSQL_dump
        - Хранение pg_dump, создаваемых на Standby PostgreSQL (VM-6)


    ##### Плюсы/минусы:

    - Плюсы:
        - Меньшее количество VM (по сравнению с другими вариантами) снижает расходы на поддержание инфраструктуры
        - Zabbix-сервер проверяет состояние компонентов приложения и отправляет уведомления системному администратору 
        - Отказоустойчивость серверов MediaWiki (VM-3, 4, 5)
            - В случае аварии на одном из серверов MediaWiki, обратный proxy-Nginx (VM-1, 2) перенаправит запрос на доступный сервер. 
        - Отказоустойчивость БД
            - В случае аварии на Primary PostgreSQL (VM-4), произойдет автоматическое переключение режима Standby PostgreSQL (VM-5) на Primary
        - Сохранность данных в БД
            - Полная актуальная копия Primary PostgreSQL (VM-4) с небольшой задержкой хранится на Standby PostgreSQL (VM-5) (задержка обусловлена асинхронным асинхронным Streaming Replication)
            - Регулярные резервные копии Standby PostgreSQL (VM-5), хранящиеся на внешнем жестком диске (HDD-1)
        - Сохранность структуры БД
            - Внешний жесткий диск (HDD-1) хранит несколько резервных копий Standby PostgreSQL (VM-5), что позволяет восстановить БД до определенной точки во времени в случае повреждения структуры на Primary PostgreSQL (VM-4) и Standby PostgreSQL (VM-5)

    - Минусы:
        - Сложная схема приложения
            - Предложенный содержит в себе сложную для настройки схему взаимодействия между VM
        - Вероятность потери небольшой части последних записанных данных
            - Асинхронная репликация между Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6) может причиной потери части данных в случае аварии на Primary PostgreSQL (VM-5)
            - Возможное решение:
                - Использование синхронной репликации данных между Primary PostgreSQL (VM-5) и Standby PostgreSQL (VM-6)  
                    - Данное решение способно замедлить общую скорость работы приложения.  
                    Стоит прибегать только в случае если критична потеря даже небольшого фрагмента последних записанных данных
        - Вероятность медленной работы приложения из-за
            - Предложенный вариант подразумевает, что VM будут выполнять несколько задач, что может негативно сказаться на отказоусточивости и скорости работы приложения
            - Возможное решение:
                - Распределение функционала на разные VM
        - Отсутствие специализированного механизма работы с медиафайлами
            - Крупные медиафайлы могут замедлить работу приложения
            - Возможное решение:
                - Добавление отдельного медиасервера для обработки медиафайлов


    ![Схема развертываемого приложения](/Solution/Mediafiles/2.1.%20App_deployment_schema_files/3.2.%20MediaWiki_app_schema.svg)   

    [Ссылка на .drawio-файл](/Solution/Mediafiles/2.1.%20App_deployment_schema_files/3.1.%20MediaWiki_app_schema.drawio)   

    </details>  
2. Создание руководства по восстановлению инфраструктуры в случае аварии
3. Проверка отказоустойчивости системы

## 3. Деплой

1. [Настройка Docker для развёртывания сервисной ВМ](Solution/3.1.%20Service%20VM%20Docker%20setup.md "Docker setup for deploying a service VM")
2. Клонирование git-репозитория в корневой каталог пользователя развернутой в Docker-контейнере ВМ
3. Настройка облачного провайдера Yandex Cloud для работы с Terraform
    1. [Установка и настройка Yandex Cloud CLI](Solution/3.3.1.%20YС%20CLI%20installation&configuration.md)
    2. [Настройка сервисного аккаунта Yandex Cloud](Solution/3.3.2.%20YC%20service%20account%20configuration.md)


