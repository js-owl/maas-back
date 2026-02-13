# Attribute Data Mapping

## Contact

| №  | Display name                  | Maas                                                                                                                                                                                                    | Type in Maas | Bitrix24            | Type in Bitrix24 |
| -- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ------------------- | ---------------- |
| 1  | Идентификатор контакта в Maas | users.id                                                                                                                                                                                                | INTEGER      | ORIGIN_ID           | string           |
| 3  | Фамилия                       | users.full_name.split(" ")[0]                                                                                                                                                                           | VARCHAR      | LAST_NAME           | string           |
| 4  | Имя                           | users.full_name.split(" ")[1]                                                                                                                                                                           | VARCHAR      | NAME                | string           |
| 5  | Отчество                      | users.full_name.split(" ")[2]                                                                                                                                                                           | VARCHAR      | SECOND_NAME         | string           |
| 6  | E-mail                        | users.email                                                                                                                                                                                             | VARCHAR      | EMAIL               | array            |
| 7  | Телефон                       | users.phone_number                                                                                                                                                                                      | VARCHAR      | PHONE               | array            |
| 8  | Почтовый индекс               | users.postal                                                                                                                                                                                            | VARCHAR      | ADDRESS_POSTAL_CODE | string           |
| 9  | Город                         | users.city                                                                                                                                                                                              | VARCHAR      | ADDRESS_CITY        | string           |
| 10 | Район                         | users.region                                                                                                                                                                                            | VARCHAR      | ADDRESS_REGION      | string           |
| 11 | Адрес                         | users.street                                                                                                                                                                                            | VARCHAR      | ADDRESS             | string           |
| 12 | Вторая строка адреса          | users.building                                                                                                                                                                                          | VARCHAR      | ADDRESS_2           | string           |
| 13 | Комментарий                   | users.payment_company_name<br>users.payment_bank_name<br>users.payment_account<br>users.payment_cor_account<br>users.payment_card_number<br>users.payment_inn<br>users.payment_kpp<br>users.payment_bik | VARCHAR      | COMMENTS            | string           |

---

## Deal

| № | Display name                | Maas                 | Type in Maas | Bitrix24             | Type in Bitrix24                                        |
| - | --------------------------- | -------------------- | ------------ | -------------------- | ------------------------------------------------------- |
| 1 | Идентификатор сделки в Maas | kits.kit_id          | INTEGER      | UF_CRM_MAAS_ID       | integer                                                 |
| 3 | Наименование сделки         | kits.kit_name        | VARCHAR      | TITLE                | string                                                  |
| 4 | Статус сделки               | kits.status          | VARCHAR      | STAGE_ID             | string                                                  |
| 5 | Предприятие-изготовитель    | kits.location        | TEXT         | UF_CRM_MANUFACTURER  | enumeration:<br>- ЦКП<br>- АО "КТ-Спектр"<br>- АО "ДМЗ" |
| 6 | Стоимость доставки          | kits.delivery_price  | FLOAT        | UF_CRM_SHIPPING_COST | double                                                  |
| 7 | Сумма сделки                | kits.total_kit_price | FLOAT        | OPPORTUNITY          | double                                                  |

---

## Product

| №  | Display name                                    | Maas                                                                | Type in Maas                  | Bitrix24                  | Type in Bitrix24                                                                                                                                                                                                                                                                                                                                                                                   |
| -- | ----------------------------------------------- | ------------------------------------------------------------------- | ----------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Идентификатор товара в Maas                     | orders.order_id                                                     | INTEGER                       | UP_CAT_MAAS_ID            | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 3  | Наименование товара                             | orders.order_name                                                   | VARCHAR                       | name                      | string                                                                                                                                                                                                                                                                                                                                                                                             |
| 4  | Обозначение товара                              | orders.order_code                                                   | VARCHAR                       | code                      | string                                                                                                                                                                                                                                                                                                                                                                                             |
| 5  | Услуга                                          | orders.service_id                                                   | TEXT                          | UP_CAT_SERVICE            | L:<br>- 3D-печать<br>- Механическая обработка<br>- Листогибочные работы<br>- Слесарные работы<br>- Термическая обработка<br>- Лазерная резка<br>- Шлифование<br>- Сварочные работы<br>- Покрасочные работы                                                                                                                                                                                         |
| 6  | Материал                                        | orders.material_id                                                  | TEXT                          | UP_CAT_MATERIAL           | L:<br>- Алюминий 1163<br>- Алюминий АД1<br>- Алюминий АД31<br>- Алюминий АК4<br>- Алюминий АМг3<br>- Алюминий АМг6<br>- Алюминий АМц<br>- Алюминий В95оч<br>- Алюминий Д16<br>- Алюминий Д16Т<br>- Бронза БрАЖМц10-3-1.5<br>- Латунь Л63<br>- Порошок PA11<br>- Порошок PA12<br>- Сталь 12Х18Н10Т<br>- Сталь 14Х17Н2<br>- Сталь 20<br>- Сталь 30ХГСА<br>- Сталь 40Х<br>- Сталь 40Х13<br>- Сталь 45 |
| 7  | Шероховатость                                   | orders.finish_id                                                    | TEXT                          | UP_CAT_ROUGHNESS          | L:<br>- 12.5<br>- 6.3<br>- 3.2<br>- 1.6<br>- 0.8                                                                                                                                                                                                                                                                                                                                                   |
| 8  | Квалитет точности                               | orders.tolerance_id                                                 | TEXT                          | UP_CAT_ACCURACY           | L:<br>- IT7<br>- IT8<br>- IT9<br>- IT10<br>- IT11<br>- IT12                                                                                                                                                                                                                                                                                                                                        |
| 9  | Подходящее оборудование                         | orders.suitable_machines                                            | TEXT                          | UP_CAT_EQUIPMENT          | S                                                                                                                                                                                                                                                                                                                                                                                                  |
| 10 | Финишная обработка изделия                      | orders.cover_id                                                     | TEXT                          | UP_CAT_FINISHING          | L:<br>- Покраска<br>- Гальваника                                                                                                                                                                                                                                                                                                                                                                   |
| 11 | Вид контроля                                    | orders.k_otk                                                        | TEXT                          | UP_CAT_CONTROL            | L:<br>- Изготовителя<br>- Заказчика на площадке изготовителя<br>- Независимой приёмкой                                                                                                                                                                                                                                                                                                             |
| 12 | Сертификаты и квалификации поставщиков          | orders.k_cert                                                       | TEXT                          | UP_CAT_CERTIFICATES       | L:<br>- a<br>- b<br>- c<br>- d<br>- e<br>- f                                                                                                                                                                                                                                                                                                                                                       |
| 13 | Время изготовления, дней                        | orders.manufacturing_cycle                                          | FLOAT                         | UP_CAT_PROD_TIME          | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 14 | 3D-модель                                       | orders.file_id                                                      | INTEGER                       | UP_CAT_3D_MODEL           | F                                                                                                                                                                                                                                                                                                                                                                                                  |
| 15 | Чертежи, документация                           | orders.document_ids                                                 | TEXT                          | UP_CAT_DOC                | F                                                                                                                                                                                                                                                                                                                                                                                                  |
| 16 | Извлечённые габаритные размеры детали           | orders.length<br>orders.width<br>orders.height                      | INTEGER<br>INTEGER<br>INTEGER | length<br>width<br>height | double<br>double<br>double                                                                                                                                                                                                                                                                                                                                                                         |
| 17 | Объём заготовки                                 | orders.mat_volume                                                   | FLOAT                         | UP_CAT_VOLUME             | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 18 | Норма расхода                                   | orders.mat_weight                                                   | FLOAT                         | UP_CAT_CONS_RATE          | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 19 | Основной материал                               | orders.total_price_breakdown["mat_price"]                           | FLOAT                         | UP_CAT_MAIN_MAT           | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 20 | Вспомогательные материалы                       | orders.total_price_breakdown["dop_mat_price"]                       | FLOAT                         | UP_CAT_SUP_MAT            | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 21 | Трудоёмкость                                    | orders.total_time                                                   | FLOAT                         | UP_CAT_INTENSITY          | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 22 | Стоимость нормочаса                             | orders.total_price_breakdown["price_of_hour_with_others"]           | FLOAT                         | UP_CAT_STND_HR_COST       | N                                                                                                                                                                                                                                                                                                                                                                                                  |
| 23 | Затраты на специальную технологическую оснастку | orders.total_price_breakdown["price_special_equipment_to_quantity"] | FLOAT                         | UP_CAT_SPEC_EQ_COST       | N                                                                                                                                                                                                                                                                                                                                                                                                  |

---

## Product row

| № | Display name                | Maas                          | Type in Maas | Bitrix24      | Type in Bitrix24 |
| - | --------------------------- | ----------------------------- | ------------ | ------------- | ---------------- |
| 1 | Стоимость товара            | orders.detail_price_one       | FLOAT        | PRICE         | double           |
| 2 | Количество                  | orders.quantity               | INTEGER      | QUANTITY      | double           |
| 3 | Размер скидки на позицию, % | (1 - orders.k_quantity) * 100 | FLOAT        | DISCOUNT_RATE | double           |

---

## Lists of values

### 1. Materials

**Request**

```
http://127.0.0.1:7000/materials
```

**Mapping**

* `data.materials[i].id` → `orders.material_id`
* `data.materials[i].label` → `UP_CAT_MATERIAL`

---

### 2. Services

**Request**

```
http://127.0.0.1:7000/auto_services
http://127.0.0.1:7000/other_services
```

**Mapping**

* `data.services[i].id` → `orders.service_id`
* `data.services[i].label` → `UP_CAT_SERVICE`

---

### 3. Locations

**Request**

```
http://127.0.0.1:7000/locations
```

**Mapping**

* `data.locations[i].id` → `kits.location`
* `data.locations[i].russian_name` → `UF_CRM_MANUFACTURER`

---

### 4. Coefficients

**Request**

```
http://127.0.0.1:7000/coefficients
```

**Mapping**

* `data.tolerance[i].id` → `orders.tolerance_id`

* `data.finish[i].id` → `orders.finish_id`

* `data.cover[i].id` → `orders.cover_id`

* `data.control_types[i].id` → `orders.k_otk`

* `data.cert_costs[i].id` → `orders.k_cert`

* `data.tolerance[i].label` → `UP_CAT_ACCURACY`

* `data.finish[i].label` → `UP_CAT_ROUGHNESS`

* `data.cover[i].label` → `UP_CAT_FINISHING`

* `data.control_types[i].label` → `UP_CAT_CONTROL`

* `data.cert_costs[i].label` → `UP_CAT_CERTIFICATES`
