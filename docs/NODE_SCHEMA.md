# Структуры данных (JSON Схемы)

Для грамотной работы распределенной системы, мы разделяем логическое представление узла (Core Node) и его визуальное представление (Canvas Node).

## 1. Core Node (Логическое ядро)
Этот JSON понятен машинам (Workers) и Оркестратору. Он описывает СУТЬ ноды: её интерфейсы и выполняемый код. Машине не важно, где находится нода на экране, ей важен этот конфиг.

```json
{
  "node_class_id": "custom_image_processor_v1",
  "name": "Поиск собаки",
  "description": "Анализирует кадр и ищет собаку",
  "runtime": "python3",
  "code": "def process(inputs, params):\n    # user python code here\n    return {'is_dog_found': True}",
  "inputs": [
    {
      "id": "in_image",
      "name": "Кадр",
      "type": "ndarray" 
    }
  ],
  "outputs": [
    {
      "id": "out_result",
      "name": "Найдена собака",
      "type": "boolean"
    }
  ],
  "parameters": [
    {
      "id": "param_confidence",
      "name": "Уверенность (Threshold)",
      "type": "float",
      "default_value": 0.8
    }
  ]
}
```

## 2. Canvas Node (Визуальная обертка)
Этот JSON используется Клиентом (React Flow) для отрисовки на канвасе и Оркестратором для понимания, где этот код должен выполняться. Он "оборачивает" Core Node.

```json
{
  "id": "instance_uuid_8f4a",
  "type": "adrn_node",
  "position": {
    "x": 350,
    "y": 120
  },
  "ui_style": {
    "color": "#4A90E2",
    "width": 250,
    "collapsed": false
  },
  "assigned_worker_id": "raspberry_pi_camera_1",
  "data": {
    "core_node_ref": "custom_image_processor_v1", 
    "parameter_values": {
      "param_confidence": 0.95
    }
  }
}
```

## 3. Edge (Связь / Топик)
Описывает соединение между нодами. Во время запуска Оркестратор добавляет сюда сетевые адреса (ZeroMQ), чтобы машины могли связаться.

```json
{
  "id": "edge_uuid_1122",
  "source_node": "instance_uuid_camera_node",
  "source_pin": "out_image",
  "target_node": "instance_uuid_8f4a",
  "target_pin": "in_image",
  "runtime_topic": {
    "protocol": "zmq_tcp",
    "address": "tcp://192.168.1.15:5555"
  }
}
```
