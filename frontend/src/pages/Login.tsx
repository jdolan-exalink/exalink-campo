import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import { useAuthStore } from '@/store/authStore'

const schema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña requerida'),
})
type FormData = z.infer<typeof schema>

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: 'admin@exalink.com', password: 'exalink2024' },
  })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      const { data: tokens } = await api.post('/auth/login', data)
      api.defaults.headers.common.Authorization = `Bearer ${tokens.access_token}`
      const { data: user } = await api.get('/auth/me')
      setAuth(user, tokens.access_token, tokens.refresh_token)
      navigate('/dashboard', { replace: true })
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-brand-600 items-center justify-center text-white font-bold text-2xl mb-4">
            EC
          </div>
          <h1 className="text-2xl font-bold text-white">Exalink Campo</h1>
          <p className="text-slate-400 mt-1 text-sm">Plataforma Ganadera Inteligente</p>
          <p className="text-slate-600 mt-1 text-xs">v{__APP_VERSION__}</p>
        </div>

        <div className="card p-8">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
              <input
                type="email"
                {...register('email')}
                className="input"
                placeholder="admin@exalink.com"
              />
              {errors.email && <p className="text-danger text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Contraseña</label>
              <input
                type="password"
                {...register('password')}
                className="input"
                placeholder="••••••••"
              />
              {errors.password && <p className="text-danger text-xs mt-1">{errors.password.message}</p>}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-2.5 mt-2"
            >
              {loading ? 'Iniciando sesión...' : 'Iniciar sesión'}
            </button>
          </form>

          <div className="mt-6 p-3 bg-surface-900 rounded-lg border border-surface-700">
            <p className="text-xs text-slate-500 text-center">Demo: admin@exalink.com / exalink2024</p>
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          Exalink Campo v{__APP_VERSION__} — Plataforma multi-tenant
        </p>
      </div>
    </div>
  )
}
