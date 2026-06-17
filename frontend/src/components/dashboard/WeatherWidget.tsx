import { useQuery } from '@tanstack/react-query'
import { Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, CloudSun, Droplets, Sun, Thermometer, Wind } from 'lucide-react'

interface WeatherData {
  current: {
    temperature: number
    weatherCode: number
    humidity: number
    windSpeed: number
    windDirection: number
  }
  daily: {
    date: string
    weatherCode: number
    tempMax: number
    tempMin: number
    precipitationProb: number
  }[]
}

function weatherIcon(code: number, size?: number) {
  const s = size ?? 28
  if (code <= 1) return Sun
  if (code === 2) return CloudSun
  if (code === 3) return Cloud
  if (code <= 49) return CloudFog
  if (code <= 59) return CloudDrizzle
  if (code <= 69) return CloudRain
  if (code <= 79) return CloudSnow
  if (code <= 89) return CloudRain
  if (code <= 99) return CloudLightning
  return Cloud
}

function weatherLabel(code: number): string {
  if (code <= 1) return 'Despejado'
  if (code === 2) return 'Parcial nublado'
  if (code === 3) return 'Nublado'
  if (code <= 49) return 'Niebla'
  if (code <= 59) return 'Llovizna'
  if (code <= 69) return 'Lluvia'
  if (code <= 79) return 'Nieve'
  if (code <= 89) return 'Lluvia fuerte'
  if (code <= 99) return 'Tormenta'
  return 'Nublado'
}

function windDirLabel(deg: number): string {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO']
  return dirs[Math.round(deg / 45) % 8]
}

export default function WeatherWidget({ lat, lon, fieldName }: { lat: number; lon: number; fieldName?: string | null }) {
  const { data, isLoading, isError } = useQuery<WeatherData>({
    queryKey: ['weather', lat.toFixed(2), lon.toFixed(2)],
    queryFn: async () => {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=America%2FArgentina%2FBuenos_Aires&forecast_days=5`
      const res = await fetch(url)
      const json = await res.json()
      return {
        current: {
          temperature: json.current.temperature_2m,
          weatherCode: json.current.weather_code,
          humidity: json.current.relative_humidity_2m,
          windSpeed: json.current.wind_speed_10m,
          windDirection: json.current.wind_direction_10m,
        },
        daily: json.daily.time.map((date: string, i: number) => ({
          date,
          weatherCode: json.daily.weather_code[i],
          tempMax: json.daily.temperature_2m_max[i],
          tempMin: json.daily.temperature_2m_min[i],
          precipitationProb: json.daily.precipitation_probability_max[i],
        })),
      }
    },
    staleTime: 10 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="card p-4 animate-pulse">
        <div className="h-4 w-24 bg-surface-700 rounded mb-3" />
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 bg-surface-700 rounded-full" />
          <div>
            <div className="h-6 w-16 bg-surface-700 rounded mb-1" />
            <div className="h-3 w-20 bg-surface-700 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="card p-4">
        <p className="text-xs text-slate-500">No se pudo cargar el clima</p>
      </div>
    )
  }

  const Icon = weatherIcon(data.current.weatherCode)

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CloudSun size={16} className="text-brand-400" />
          <h3 className="text-sm font-semibold text-slate-300">Clima{fieldName ? ` — ${fieldName}` : ''}</h3>
        </div>
        <span className="text-[10px] text-slate-500">Open-Meteo</span>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-1">
          <Icon size={36} className="text-sky-400" />
        </div>
        <div>
          <p className="text-3xl font-bold text-white tabular-nums">
            {data.current.temperature.toFixed(0)}°
          </p>
          <p className="text-xs text-slate-400">{weatherLabel(data.current.weatherCode)}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 py-3 border-t border-b border-surface-700">
        <div className="flex items-center gap-1.5">
          <Droplets size={14} className="text-cyan-400" />
          <div>
            <p className="text-xs text-slate-400">Humedad</p>
            <p className="text-sm font-semibold text-white tabular-nums">{data.current.humidity}%</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Wind size={14} className="text-teal-400" />
          <div>
            <p className="text-xs text-slate-400">Viento</p>
            <p className="text-sm font-semibold text-white tabular-nums">
              {data.current.windSpeed.toFixed(0)} km/h
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Thermometer size={14} className="text-orange-400" />
          <div>
            <p className="text-xs text-slate-400">Sensación</p>
            <p className="text-sm font-semibold text-white tabular-nums">
              {data.current.temperature.toFixed(0)}°
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-between mt-3">
        {data.daily.slice(1, 6).map((day) => {
          const DayIcon = weatherIcon(day.weatherCode)
          const dayName = new Date(day.date + 'T00:00:00').toLocaleDateString('es-AR', { weekday: 'short' })
          return (
            <div key={day.date} className="flex flex-col items-center gap-1">
              <span className="text-[10px] text-slate-500 uppercase">{dayName}</span>
              <DayIcon size={18} className="text-sky-400" />
              <p className="text-xs font-semibold text-white tabular-nums">{day.tempMax.toFixed(0)}°</p>
              <p className="text-[10px] text-slate-500 tabular-nums">{day.tempMin.toFixed(0)}°</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
