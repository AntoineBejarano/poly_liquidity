import { SignIn } from '@stackframe/stack';

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="w-full max-w-md">
        <div className="glass rounded-2xl p-8 shadow-premium animate-fade-in">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg">
              <span className="text-3xl font-bold text-white">A</span>
            </div>
            <h1 className="text-3xl font-bold text-gradient mb-2">
              AlphaEdge
            </h1>
            <p className="text-slate-600 text-sm">
              Sistema de trading institucional de alta frecuencia
            </p>
          </div>
          <div className="mt-6">
            <SignIn />
          </div>
        </div>
        <p className="text-center text-xs text-slate-500 mt-6">
          Plataforma profesional para gestión de liquidez en mercados de predicción
        </p>
      </div>
    </div>
  );
}

