// Web Bluetooth RFID reader integration
// Nordic UART Service (NUS) — most common BLE-RFID adapter protocol
// RX char (device→browser): 6e400003-b5a3-f393-e0a9-e50e24dcca9e

const NUS_SERVICE = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
const NUS_RX_CHAR = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'

export type RFIDReadCallback = (rfid: string) => void
export type BTStatusCallback = (status: BTStatus) => void
export type BTStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyBT = any

let _device: AnyBT = null
let _server: AnyBT = null
let _rxChar: AnyBT = null
let _onRead: RFIDReadCallback | null = null
let _onStatus: BTStatusCallback | null = null
let _buffer = ''

function notify(status: BTStatus) { _onStatus?.(status) }

function handleNotification(event: Event) {
  const char = event.target as AnyBT
  if (!char?.value) return

  const chunk = new TextDecoder().decode(char.value)
  _buffer += chunk

  const lines = _buffer.split(/[\r\n]+/)
  _buffer = lines.pop() ?? ''

  for (const line of lines) {
    const rfid = line.trim()
    if (rfid && rfid.length >= 10) _onRead?.(rfid)
  }
}

export function isBluetoothAvailable(): boolean {
  return typeof navigator !== 'undefined' && 'bluetooth' in navigator
}

export async function connectRFIDReader(
  onRead: RFIDReadCallback,
  onStatus: BTStatusCallback,
): Promise<void> {
  if (!isBluetoothAvailable()) {
    throw new Error('Web Bluetooth no disponible en este navegador')
  }

  _onRead = onRead
  _onStatus = onStatus

  const bt = (navigator as AnyBT).bluetooth

  try {
    notify('connecting')
    _device = await bt.requestDevice({ filters: [{ services: [NUS_SERVICE] }] })

    _device.addEventListener('gattserverdisconnected', () => {
      notify('disconnected')
      _server = null
      _rxChar = null
    })

    _server = await _device.gatt.connect()
    const service = await _server.getPrimaryService(NUS_SERVICE)
    _rxChar = await service.getCharacteristic(NUS_RX_CHAR)

    await _rxChar.startNotifications()
    _rxChar.addEventListener('characteristicvaluechanged', handleNotification)
    notify('connected')
  } catch (e) {
    notify('error')
    _device = null
    _server = null
    _rxChar = null
    throw e
  }
}

export async function disconnectRFIDReader(): Promise<void> {
  if (_rxChar) {
    try {
      _rxChar.removeEventListener('characteristicvaluechanged', handleNotification)
      await _rxChar.stopNotifications()
    } catch { /* ignore */ }
  }
  if (_server?.connected) _device?.gatt?.disconnect()
  _device = null
  _server = null
  _rxChar = null
  _buffer = ''
  notify('disconnected')
}

export function getConnectedDeviceName(): string | null {
  return _device?.name ?? null
}
