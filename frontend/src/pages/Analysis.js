import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Loader2, CheckCircle, XCircle, ArrowLeft, Home, X } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const Analysis = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('initializing');
  const [progress, setProgress] = useState(0);
  const [stats, setStats] = useState({});
  const [currentStage, setCurrentStage] = useState('Initialisation...');
  const [error, setError] = useState(null);

  useEffect(() => {
    startProcessing();
    const interval = setInterval(checkStatus, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const startProcessing = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/session/${sessionId}/process`);
    } catch (error) {
      console.error('Error starting processing:', error);
      setError('Erreur lors du démarrage du traitement');
    }
  };

  const checkStatus = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/session/${sessionId}/status`);
      const data = response.data;

      setStatus(data.status);
      setProgress(data.progress || 0);
      setStats(data.stats || {});
      setCurrentStage(data.current_stage || 'En cours...');

      if (data.status === 'completed') {
        setTimeout(() => {
          navigate(`/results/${sessionId}`);
        }, 1500);
      } else if (data.status === 'failed') {
        setError(data.error || 'Erreur inconnue');
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const handleCancel = async () => {
    if (window.confirm('Êtes-vous sûr de vouloir annuler le traitement?')) {
      try {
        await axios.post(`${BACKEND_URL}/api/session/${sessionId}/cancel`);
        navigate('/');
      } catch (error) {
        console.error('Error canceling:', error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-4 mb-4">
            <img 
              src="/logo.png" 
              alt="ScanFlow Pro Logo" 
              className="w-12 h-12 object-contain"
            />
            <h1 className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-600" data-testid="app-title">
              ScanFlow Pro V7
            </h1>
          </div>
          <p className="text-xl text-slate-400">
            Analyse et Traitement en cours...
          </p>
        </div>

        <div className="flex gap-3 mb-6">
          <Button
            onClick={() => navigate('/')}
            variant="outline"
            className="border-slate-600 text-slate-300 hover:bg-slate-800"
          >
            <Home className="w-4 h-4 mr-2" />
            Accueil
          </Button>
          <Button
            onClick={handleCancel}
            variant="outline"
            className="border-red-600 text-red-400 hover:bg-red-500/20"
          >
            <X className="w-4 h-4 mr-2" />
            Annuler
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gradient-to-br from-indigo-500/20 to-indigo-600/20 border-2 border-indigo-500/30 rounded-xl p-6">
            <div className="text-sm text-indigo-300 mb-1">Pages Totales</div>
            <div className="text-3xl font-bold text-white">{stats.total || 0}</div>
          </div>
          <div className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 border-2 border-emerald-500/30 rounded-xl p-6">
            <div className="text-sm text-emerald-300 mb-1">Pages Traitées</div>
            <div className="text-3xl font-bold text-white">{stats.processed || 0}</div>
          </div>
          <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 border-2 border-purple-500/30 rounded-xl p-6">
            <div className="text-sm text-purple-300 mb-1">Codes Détectés</div>
            <div className="text-3xl font-bold text-white">{stats.codes || 0}</div>
          </div>
        </div>

        <Card className="bg-slate-900/90 border-2 border-slate-700 p-8">
          <div className="text-center space-y-6">
            {status === 'failed' || error ? (
              <>
                <XCircle className="w-20 h-20 text-red-500 mx-auto animate-pulse" />
                <h2 className="text-3xl font-bold text-red-400">
                  Erreur de traitement
                </h2>
                <p className="text-slate-300 text-lg">
                  {error || 'Une erreur est survenue'}
                </p>
                <Button
                  onClick={() => navigate('/')}
                  className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white font-bold h-14 px-8"
                >
                  Retour à l'accueil
                </Button>
              </>
            ) : status === 'completed' ? (
              <>
                <CheckCircle className="w-20 h-20 text-emerald-500 mx-auto animate-bounce" />
                <h2 className="text-3xl font-bold text-emerald-400">
                  Traitement terminé!
                </h2>
                <p className="text-slate-300 text-lg">
                  Redirection vers les résultats...
                </p>
              </>
            ) : (
              <>
                <Loader2 className="w-20 h-20 text-indigo-500 mx-auto animate-spin" />
                <h2 className="text-3xl font-bold text-slate-100">
                  {currentStage}
                </h2>
                
                <div className="max-w-2xl mx-auto">
                  <div className="relative h-8 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-500 ease-out flex items-center justify-center"
                      style={{ width: `${progress}%` }}
                    >
                      {progress > 10 && (
                        <span className="text-white font-bold text-sm">
                          {progress}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div className={`p-3 rounded-lg ${['initializing', 'processing'].includes(status) ? 'bg-indigo-500/20 border-2 border-indigo-500/50' : 'bg-slate-800/50'}`}>
                    <div className="text-slate-400 mb-1">Initialisation</div>
                    <div className="text-slate-200 font-bold">
                      {['initializing', 'processing', 'completed'].includes(status) ? '✓' : '●'}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg ${status === 'processing' ? 'bg-indigo-500/20 border-2 border-indigo-500/50' : 'bg-slate-800/50'}`}>
                    <div className="text-slate-400 mb-1">Traitement</div>
                    <div className="text-slate-200 font-bold">
                      {['processing', 'completed'].includes(status) ? '✓' : '●'}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg ${status === 'analyzing' ? 'bg-indigo-500/20 border-2 border-indigo-500/50' : 'bg-slate-800/50'}`}>
                    <div className="text-slate-400 mb-1">Analyse</div>
                    <div className="text-slate-200 font-bold">
                      {['analyzing', 'completed'].includes(status) ? '✓' : '●'}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg ${status === 'completed' ? 'bg-emerald-500/20 border-2 border-emerald-500/50' : 'bg-slate-800/50'}`}>
                    <div className="text-slate-400 mb-1">Terminé</div>
                    <div className="text-slate-200 font-bold">
                      {status === 'completed' ? '✓' : '●'}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Analysis;
