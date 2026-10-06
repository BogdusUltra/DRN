# Структуры данных (JSON Схемы)

## 1. Core Node (Логическое ядро)
Этот JSON понятен машинам (Workers) и Оркестратору. Теперь код обернут в Класс для поддержки состояния (State) и свободы выбора архитектуры (while True или event-driven).

```json
{
  "node_class_id": "custom_image_processor_v1",
  "name": "Поиск собаки",
  "runtime": "python3",
  "requirements": ["opencv-python", "torch"], // Зависимости (скачиваются через локальный прокси)
  "code": "class Node:\n    def __init__(self, params):\n        self.params = params\n        self.model = None # Загрузка модели\n        self.counter = 0\n\n    def on_start(self):\n        pass # Вызывается при запуске сети (можно запустить while True поток)\n\n    def process(self, inputs):\n        # Вызывается при получении новых данных на вход (event-driven)\n        self.counter += 1\n        return {'is_dog_found': True}",
  "inputs": [{"id": "in_1", "name": "Кадр", "type": "ndarray"}],
  "outputs": [{"id": "out_1", "name": "Результат", "type": "boolean"}],
  "parameters": [
    {"id": "threshold", "name": "Уверенность", "type": "float", "default_value": 0.8}
  ]
}
```

## 2. Canvas Node (Визуальная обертка)
```json
{
  "id": "instance_uuid_8f4a",
  "type": "adrn_node",
  "position": { "x": 350, "y": 120 },
  "assigned_worker_id": "raspberry_pi_camera_1",
  "data": {
    "core_node_ref": "custom_image_processor_v1", 
    "parameter_values": { "threshold": 0.95 }
  }
}
```

## 3. Edge (Связь / Топик)
```json
{
  "id": "edge_uuid_1122",
  "source_node": "uuid_камеры",
  "source_pin": "out_1",
  "target_node": "instance_uuid_8f4a",
  "target_pin": "in_1",
  "connection_type": "stream", // 'stream' (выкидывать старые) или 'default' (гарантированная доставка)
  "runtime_topic": {
    "protocol": "zmq_tcp",
    "address": "tcp://192.168.1.15:5555"
  }
}
```
