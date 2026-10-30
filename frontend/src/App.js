import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from './components/ui/sonner';
import Upload from './pages/Upload';
import Analysis from './pages/Analysis';
import Results from './pages/Results';
import '@/App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="App" dir="rtl">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/analysis/:sessionId" element={<Analysis />} />
          <Route path="/results/:sessionId" element={<Results />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster position="top-center" richColors dir="rtl" />
      </div>
    </BrowserRouter>
  );
}

export default App;
