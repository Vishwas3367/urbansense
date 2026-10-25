import { useState } from 'react';
import { ArrowRight, Wifi } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const result = await api.login(email, password);
      sessionStorage.setItem('urbansense_token', result.access_token);
      navigate('/dashboard');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-[#07111f] p-5">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/[.025] p-8 shadow-2xl shadow-black/30">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-cyan-400/10 text-cyan-300">
          <Wifi />
        </div>

        <div className="mt-5 text-center">
          <h1 className="text-2xl font-bold">UrbanSense</h1>
          <p className="mt-1 text-xs text-slate-500">
            Mobile Sensing. Intelligent Detection. Predictive Maintenance.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-2 block text-xs text-slate-500">Email</label>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="username"
              required
              className="w-full rounded-xl border border-white/10 bg-black/10 p-3 text-sm outline-none focus:border-cyan-400/30"
              placeholder="admin@urbansense.local"
            />
          </div>

          <div>
            <label className="mb-2 block text-xs text-slate-500">Password</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
              className="w-full rounded-xl border border-white/10 bg-black/10 p-3 text-sm outline-none focus:border-cyan-400/30"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-400 p-3 text-sm font-bold text-slate-950 hover:bg-cyan-300 disabled:cursor-wait disabled:opacity-60"
          >
            {isSubmitting ? 'Signing in…' : 'Sign In'}
            <ArrowRight size={17} />
          </button>

          {error && <p role="alert" className="text-center text-xs text-red-500">{error}</p>}
          <p className="text-center text-[11px] text-slate-600">Sign in with the dashboard credentials configured for the backend.</p>
        </form>
      </div>
    </div>
  );
}
