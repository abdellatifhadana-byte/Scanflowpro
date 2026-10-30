import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import ROISelector from '../components/ROISelector';
import { 
  Upload as UploadIcon, FileText, Settings, Check, X, 
  Loader2, Zap, Home, Trash2 
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const Upload = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  
  const [batchName, setBatchName] = useState('');
  const [files, setFiles] = useState([]);
  const [turboMode, setTurboMode] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false); // منع الضغط المزدوج
  
  // Settings modal
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [selectedFileIndex, setSelectedFileIndex] = useState(null);
  const [fileSettings, setFileSettings] = useState({});
  const [previewImage, setPreviewImage] = useState(null);
  const [loadingImage, setLoadingImage] = useState({});

  const onDrop = useCallback(async (e) => {
    e.preventDefault();
    
    // منع المعالجة المتعددة
    if (isProcessing) return;
    setIsProcessing(true);
    
    try {
      const droppedFiles = Array.from(e.dataTransfer?.files || e.target.files || []);
      const pdfFiles = droppedFiles.filter(file => file.type === 'application/pdf');
      
      if (pdfFiles.length === 0) {
        toast.error('Veuillez sélectionner des fichiers PDF');
        return;
      }

      const filesWithInfo = await Promise.all(pdfFiles.map(async (file) => {
        try {
          const formData = new FormData();
          formData.append('file', file);
          
          const response = await axios.post(`${BACKEND_URL}/api/pdf/info`, formData, {
            timeout: 30000 // 30 second timeout
          });
          return {
            file,
            preview: null,
            pageCount: response.data?.page_count || 0,
            fileSize: file.size
          };
        } catch (error) {
          console.error('Error getting PDF info:', error);
          return {
            file,
            preview: null,
            pageCount: 0,
            fileSize: file.size
          };
        }
      }));

      setFiles(prev => [...(prev || []), ...filesWithInfo]);
      toast.success(`${pdfFiles.length} fichier(s) ajouté(s)`);
    } finally {
      setIsProcessing(false);
    }
  }, [isProcessing]);

  const openSettingsModal = useCallback(async (index) => {
    if (!files || !files[index]) return;
    
    setSelectedFileIndex(index);
    setShowSettingsModal(true);
    
    const fileName = files[index]?.file?.name;
    if (fileName && !fileSettings[fileName]) {
      setFileSettings(prev => ({
        ...(prev || {}),
        [fileName]: {
          outputName: fileName.replace('.pdf', ''),
          keyword: '',
          documentType: 'printed',
          childPagesMode: 'auto',
          childPagesCount: 0,
          roiAreas: []
        }
      }));
    }

    if (files[index]?.file) {
      await loadPreviewImage(files[index].file);
    }
  }, [files, fileSettings]);

  const loadPreviewImage = async (file) => {
    setLoadingImage(prev => ({ ...prev, [file.name]: true }));
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(`${BACKEND_URL}/api/pdf/first-page`, formData, {
        responseType: 'blob'
      });
      
      const imageUrl = URL.createObjectURL(response.data);
      setPreviewImage(imageUrl);
    } catch (error) {
      console.error('Error loading preview:', error);
      toast.error('Erreur lors du chargement de l\'aperçu');
    } finally {
      setLoadingImage(prev => ({ ...prev, [file.name]: false }));
    }
  };

  const saveSettings = () => {
    const fileName = files[selectedFileIndex].file.name;
    toast.success(`✓ Paramètres sauvegardés pour ${fileName}`);
    setShowSettingsModal(false);
  };

  const closeSettingsModal = () => {
    setShowSettingsModal(false);
    setPreviewImage(null);
  };

  const updateFileSetting = (field, value) => {
    const fileName = files[selectedFileIndex].file.name;
    setFileSettings({
      ...fileSettings,
      [fileName]: {
        ...fileSettings[fileName],
        [field]: value
      }
    });
  };

  const handleROISave = (rois) => {
    const fileName = files[selectedFileIndex].file.name;
    setFileSettings({
      ...fileSettings,
      [fileName]: {
        ...fileSettings[fileName],
        roiAreas: rois
      }
    });
    toast.success('✓ ROIs sauvegardés');
  };

  const removeFile = (index) => {
    const newFiles = files.filter((_, i) => i !== index);
    setFiles(newFiles);
    toast.success('Fichier supprimé');
  };

  const handleSubmit = async () => {
    if (!batchName.trim()) {
      toast.error('⚠️ Veuillez entrer un nom de lot');
      return;
    }

    if (files.length === 0) {
      toast.error('⚠️ Veuillez ajouter au moins un fichier');
      return;
    }

    setUploading(true);

    try {
      const sessionData = {
        batch_name: batchName,
        turbo_mode: turboMode,
        file_settings: files.map(f => {
          const settings = fileSettings[f.file.name] || {};
          return {
            filename: f.file.name,
            output_name: settings.outputName || f.file.name.replace('.pdf', ''),
            keyword: settings.keyword || '',
            document_type: settings.documentType || 'printed',
            child_pages_mode: settings.childPagesMode || 'auto',
            child_pages_count: settings.childPagesCount || 0,
            roi_areas: settings.roiAreas || []
          };
        })
      };

      const sessionResponse = await axios.post(`${BACKEND_URL}/api/session/create`, sessionData);
      const sessionId = sessionResponse.data.session_id;

      const formData = new FormData();
      files.forEach(f => formData.append('files', f.file));

      await axios.post(`${BACKEND_URL}/api/session/${sessionId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success('✅ Fichiers téléchargés avec succès!');
      navigate(`/analysis/${sessionId}`);
      
    } catch (error) {
      console.error('Error:', error);
      toast.error('❌ Erreur lors du téléchargement');
    } finally {
      setUploading(false);
    }
  };

  const currentSettings = selectedFileIndex !== null ? 
    fileSettings[files[selectedFileIndex]?.file.name] || {} : {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        
        {/* العنوان مع اللوغو */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-4 mb-4">
            <img 
              src="/logo.png" 
              alt="ScanFlow Pro Logo" 
              className="w-16 h-16 md:w-20 md:h-20 object-contain"
            />
            <h1 className="text-5xl md:text-6xl font-black bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-600 text-transparent bg-clip-text">
              ScanFlow Pro V7
            </h1>
          </div>
          <p className="text-xl text-slate-300 font-light">
            Système intelligent de traitement PDF par lots
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
        </div>

        <Card className="mb-8 bg-slate-900/90 border-2 border-slate-700 p-8">
          <div className="space-y-6">
            <div>
              <Label className="text-slate-200 text-lg mb-2 block">
                📦 Nom du lot
              </Label>
              <Input
                data-testid="batch-name-input"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="Ex: Dossiers_Parcelles_2025"
                className="bg-slate-800/50 border-slate-600 text-slate-100 text-lg h-14"
              />
            </div>

            <div className="flex items-center gap-4 p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-lg">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={turboMode}
                  onChange={(e) => setTurboMode(e.target.checked)}
                  className="w-5 h-5"
                />
                <Zap className="w-6 h-6 text-yellow-400" />
                <span className="text-slate-200 font-bold">Mode Turbo</span>
              </label>
              <span className="text-sm text-slate-400 ml-auto">
                Traitement plus rapide (précision standard)
              </span>
            </div>
          </div>
        </Card>

        <Card className="mb-8 bg-slate-900/90 border-2 border-slate-700 p-8">
          <Label className="text-slate-200 text-lg mb-4 block">
            📁 Fichiers PDF
          </Label>

          <div
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-600 rounded-xl p-12 text-center cursor-pointer hover:border-indigo-500 hover:bg-slate-800/50 transition-all"
          >
            <UploadIcon className="w-16 h-16 text-slate-500 mx-auto mb-4" />
            <p className="text-slate-300 text-lg mb-2">
              Glissez-déposez vos fichiers PDF ici
            </p>
            <p className="text-slate-500 text-sm">
              ou cliquez pour parcourir
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf"
              onChange={onDrop}
              className="hidden"
            />
          </div>

          {files.length > 0 && (
            <div className="mt-6 space-y-3">
              {files.map((f, index) => {
                const settings = fileSettings[f.file.name] || {};
                const hasSettings = settings.outputName || settings.keyword || settings.documentType || settings.childPagesMode;
                
                return (
                  <div key={index} className="bg-slate-800/50 border border-slate-700 rounded-lg hover:bg-slate-800 transition overflow-hidden">
                    {/* معلومات الملف الأساسية */}
                    <div className="flex items-center gap-4 p-4">
                      <FileText className="w-8 h-8 text-indigo-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-slate-100 text-lg truncate">{f.file.name}</p>
                        <div className="flex gap-4 text-sm text-slate-400 mt-1">
                          <span>📄 {f.pageCount || '?'} page(s)</span>
                          <span>💾 {(f.file.size / 1024).toFixed(2)} KB</span>
                        </div>
                      </div>
                      <Button
                        onClick={() => openSettingsModal(index)}
                        className="bg-indigo-600 hover:bg-indigo-700 flex-shrink-0"
                      >
                        <Settings className="w-4 h-4 mr-2" />
                        Paramètres
                      </Button>
                      <Button
                        onClick={() => removeFile(index)}
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/20 flex-shrink-0"
                      >
                        <Trash2 className="w-5 h-5" />
                      </Button>
                    </div>

                    {/* عرض الإعدادات المحفوظة */}
                    {hasSettings && (
                      <div className="px-4 pb-4 pt-2 border-t border-slate-700/50">
                        <div className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <Check className="w-4 h-4 text-emerald-400" />
                            <span className="text-sm font-bold text-emerald-400">Paramètres configurés</span>
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                            {settings.outputName && (
                              <div className="flex items-start gap-2">
                                <span className="text-slate-400">📝 Nom de sortie:</span>
                                <span className="text-slate-200 font-semibold">{settings.outputName}</span>
                              </div>
                            )}
                            
                            {settings.keyword && (
                              <div className="flex items-start gap-2">
                                <span className="text-slate-400">🔑 Mot-clé:</span>
                                <span className="text-slate-200 font-semibold">{settings.keyword}</span>
                              </div>
                            )}
                            
                            {settings.documentType && (
                              <div className="flex items-start gap-2">
                                <span className="text-slate-400">📄 Type:</span>
                                <span className="text-slate-200 font-semibold">
                                  {settings.documentType === 'printed' ? '🖨️ Imprimé (OCR)' :
                                   settings.documentType === 'handwritten' ? '✍️ Manuscrit (HTR)' :
                                   '🔀 Mixte (OCR + HTR)'}
                                </span>
                              </div>
                            )}
                            
                            {settings.childPagesMode && (
                              <div className="flex items-start gap-2">
                                <span className="text-slate-400">👶 Pages enfants:</span>
                                <span className="text-slate-200 font-semibold">
                                  {settings.childPagesMode === 'auto' ? '🤖 Auto' :
                                   settings.childPagesMode === 'none' ? '❌ Aucune' :
                                   settings.childPagesMode === 'fixed' ? `📊 Fixe (${settings.childPagesCount || 0})` :
                                   settings.childPagesMode === 'marker' ? '🏷️ Marqueur' :
                                   '⚡ Dynamique'}
                                </span>
                              </div>
                            )}
                            
                            {settings.roiAreas && settings.roiAreas.length > 0 && (
                              <div className="flex items-start gap-2 col-span-full">
                                <span className="text-slate-400">🎯 ROIs:</span>
                                <div className="flex flex-wrap gap-2">
                                  {settings.roiAreas.map((roi, idx) => (
                                    <span key={idx} className="px-2 py-1 bg-slate-700/50 rounded text-xs font-semibold">
                                      {roi.type === 'code' ? '🔵 Code' :
                                       roi.type === 'keyword' ? '🟢 Keyword' :
                                       '🟠 Marker'}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {files.length > 0 && (
          <Button
            onClick={handleSubmit}
            disabled={uploading}
            className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-bold h-16 text-xl shadow-2xl"
          >
            {uploading ? (
              <>
                <Loader2 className="animate-spin w-6 h-6 mr-3" />
                Téléchargement en cours...
              </>
            ) : (
              <>
                <Check className="w-6 h-6 mr-3" />
                Démarrer le traitement
              </>
            )}
          </Button>
        )}

        {showSettingsModal && selectedFileIndex !== null && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closeSettingsModal}>
            <div className="bg-slate-900 border-2 border-indigo-500 rounded-2xl max-w-5xl w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
              <div className="sticky top-0 bg-slate-900 border-b-2 border-slate-700 p-6 flex items-center justify-between z-10">
                <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
                  ⚙️ Paramètres: {files[selectedFileIndex].file.name}
                </h2>
                <Button variant="ghost" onClick={closeSettingsModal}>
                  <X className="w-6 h-6" />
                </Button>
              </div>

              <div className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label className="text-slate-200 mb-2 block">Nom de sortie</Label>
                    <Input
                      value={currentSettings.outputName || ''}
                      onChange={(e) => updateFileSetting('outputName', e.target.value)}
                      placeholder="Ex: PLAN_CADASTRAL"
                      className="bg-slate-800/50 border-slate-600 text-slate-100"
                    />
                  </div>

                  <div>
                    <Label className="text-slate-200 mb-2 block">Mot-clé (Keyword)</Label>
                    <Input
                      value={currentSettings.keyword || ''}
                      onChange={(e) => updateFileSetting('keyword', e.target.value)}
                      placeholder="Ex: Parcelle N°, رقم القطعة"
                      className="bg-slate-800/50 border-slate-600 text-slate-100"
                    />
                  </div>

                  <div>
                    <Label className="text-slate-200 mb-2 block">Type de document</Label>
                    <Select 
                      value={currentSettings.documentType || 'printed'} 
                      onValueChange={(v) => updateFileSetting('documentType', v)}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-slate-100">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="printed">Imprimé (OCR)</SelectItem>
                        <SelectItem value="handwritten">Manuscrit (HTR)</SelectItem>
                        <SelectItem value="mixed">Mixte (OCR + HTR)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-slate-200 mb-2 block">Pages enfants</Label>
                    <Select 
                      value={currentSettings.childPagesMode || 'auto'} 
                      onValueChange={(v) => updateFileSetting('childPagesMode', v)}
                    >
                      <SelectTrigger className="bg-slate-800/50 border-slate-600 text-slate-100">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto (Détection automatique)</SelectItem>
                        <SelectItem value="none">Aucune</SelectItem>
                        <SelectItem value="fixed">Fixe (nombre)</SelectItem>
                        <SelectItem value="marker">Marqueur (1/3, 2/3...)</SelectItem>
                        <SelectItem value="dynamic">Dynamique</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {currentSettings.childPagesMode === 'fixed' && (
                    <div>
                      <Label className="text-slate-200 mb-2 block">Nombre de pages enfants</Label>
                      <Input
                        type="number"
                        min="0"
                        value={currentSettings.childPagesCount || 0}
                        onChange={(e) => updateFileSetting('childPagesCount', parseInt(e.target.value))}
                        className="bg-slate-800/50 border-slate-600 text-slate-100"
                      />
                    </div>
                  )}
                </div>

                <div className="border-t-2 border-slate-700 pt-6">
                  <Label className="text-slate-200 text-lg mb-4 block">
                    🎯 Zones ROI (Regions of Interest)
                  </Label>
                  
                  {loadingImage[files[selectedFileIndex].file.name] ? (
                    <div className="text-center py-12">
                      <Loader2 className="animate-spin h-10 w-10 text-indigo-500 mx-auto mb-3" />
                      <p className="text-base text-slate-400">Chargement de l'aperçu...</p>
                    </div>
                  ) : previewImage ? (
                    <ROISelector
                      imageUrl={previewImage}
                      onSave={handleROISave}
                      initialROIs={currentSettings.roiAreas || []}
                    />
                  ) : (
                    <div className="text-center py-12 text-slate-400">
                      Aucun aperçu disponible
                    </div>
                  )}
                </div>
              </div>

              <div className="sticky bottom-0 bg-slate-900 border-t-2 border-slate-700 p-6 flex gap-4">
                <Button
                  onClick={saveSettings}
                  className="flex-1 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-bold h-14 text-lg shadow-xl shadow-emerald-500/30"
                >
                  <Check className="w-6 h-6 mr-2" />
                  Sauvegarder les paramètres
                </Button>
                <Button
                  variant="outline"
                  onClick={closeSettingsModal}
                  className="border-slate-600 text-slate-300 hover:bg-slate-800 h-14 px-8"
                >
                  Annuler
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
