import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { 
  ArrowLeft, Download, FileText, Edit2, Trash2, Eye, 
  CheckCircle, XCircle, Search, Filter, Package, FolderOpen,
  Save, RefreshCw, SortAsc, SortDesc, Folder, FileCheck,
  Home, ArrowUp, ArrowDown, Move, Info, Trash, Database
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const Results = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [pages, setPages] = useState([]);
  const [codeGroups, setCodeGroups] = useState({});
  const [loading, setLoading] = useState(true);
  const [editingCell, setEditingCell] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCode, setFilterCode] = useState('all');
  const [filterSourceFile, setFilterSourceFile] = useState('all');
  const [filterOutputName, setFilterOutputName] = useState('all');
  const [sortField, setSortField] = useState('page_number');
  const [sortDirection, setSortDirection] = useState('asc');
  const [showFinalSummary, setShowFinalSummary] = useState(false);
  const [showMergeSettings, setShowMergeSettings] = useState(false);
  const [showFolderPreview, setShowFolderPreview] = useState(false);
  const [showDecisionLog, setShowDecisionLog] = useState(false);
  const [showPreviewPDF, setShowPreviewPDF] = useState(false);
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [selectedPage, setSelectedPage] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [merging, setMerging] = useState(false);
  const [finalStructure, setFinalStructure] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [moveToCode, setMoveToCode] = useState('');

  useEffect(() => {
    fetchResults();
  }, [sessionId]);

  useEffect(() => {
    const groups = {};
    pages.forEach(page => {
      const code = page.code || 'NO_CODE';
      if (!groups[code]) {
        groups[code] = [];
      }
      groups[code].push(page);
    });
    setCodeGroups(groups);
  }, [pages]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${BACKEND_URL}/api/session/${sessionId}/results`);
      setPages(response.data.pages || []);
    } catch (error) {
      console.error('Erreur:', error);
      toast.error('Erreur lors du chargement des résultats');
    } finally {
      setLoading(false);
    }
  };

  const updatePage = async (pageId, field, value) => {
    try {
      await axios.put(`${BACKEND_URL}/api/session/${sessionId}/page`, {
        page_id: pageId,
        [field]: value
      });
      toast.success('✅ Mis à jour avec succès');
      fetchResults();
    } catch (error) {
      console.error('Erreur:', error);
      toast.error('❌ Erreur lors de la mise à jour');
    }
  };

  const deletePage = async (pageId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer cette page?')) return;
    
    try {
      await axios.delete(`${BACKEND_URL}/api/session/${sessionId}/page/${pageId}`);
      toast.success('✅ Page supprimée');
      fetchResults();
    } catch (error) {
      console.error('Erreur:', error);
      toast.error('❌ Erreur lors de la suppression');
    }
  };

  const handleMovePage = async () => {
    if (!selectedPage || !moveToCode) return;

    try {
      await axios.post(`${BACKEND_URL}/api/session/${sessionId}/move-page`, {
        page_id: selectedPage.page_id,
        new_code: moveToCode
      });
      toast.success('✅ Page déplacée');
      setShowMoveModal(false);
      setSelectedPage(null);
      setMoveToCode('');
      fetchResults();
    } catch (error) {
      toast.error('❌ Erreur lors du déplacement');
    }
  };

  const handleReorderPage = async (pageId, direction) => {
    const page = pages.find(p => p.page_id === pageId);
    if (!page) return;

    const code = page.code;
    const groupPages = codeGroups[code] || [];
    const currentIndex = groupPages.findIndex(p => p.page_id === pageId);
    
    if (direction === 'up' && currentIndex === 0) return;
    if (direction === 'down' && currentIndex === groupPages.length - 1) return;

    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    const newOrder = [...groupPages];
    [newOrder[currentIndex], newOrder[newIndex]] = [newOrder[newIndex], newOrder[currentIndex]];

    try {
      await axios.put(`${BACKEND_URL}/api/session/${sessionId}/reorder-pages`, {
        code: code,
        new_order: newOrder.map(p => p.page_id)
      });
      toast.success('✅ Ordre modifié');
      fetchResults();
    } catch (error) {
      toast.error('❌ Erreur lors du réordonnancement');
    }
  };

  const clearCache = async () => {
    try {
      const response = await axios.post(`${BACKEND_URL}/api/clear-cache`);
      toast.success(`✅ ${response.data.cleared_count} fichiers temporaires supprimés`);
    } catch (error) {
      toast.error('❌ Erreur lors du nettoyage');
    }
  };

  const clearOldFiles = async () => {
    if (!window.confirm('Supprimer les fichiers de plus de 7 jours?')) return;

    try {
      const response = await axios.post(`${BACKEND_URL}/api/clear-old-files?days=7`);
      toast.success(`✅ ${response.data.deleted_count} fichiers supprimés (${response.data.deleted_size_mb} MB)`);
    } catch (error) {
      toast.error('❌ Erreur lors du nettoyage');
    }
  };

  const showDecisionLogModal = (page) => {
    setSelectedPage(page);
    setShowDecisionLog(true);
  };

  const previewPDF = async (code) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/session/${sessionId}/preview/${code}`);
      setPreviewData(response.data);
      setShowPreviewPDF(true);
    } catch (error) {
      toast.error('❌ Erreur lors de la prévisualisation');
    }
  };

  const previewFinalStructure = () => {
    const structure = {};
    
    Object.entries(codeGroups).forEach(([code, groupPages]) => {
      if (code === 'NO_CODE') return;
      
      structure[code] = {
        folder: `P${code}`,
        files: {}
      };
      
      groupPages.forEach(page => {
        const outputName = page.output_name || 'DEFAULT';
        const sourceFile = page.source_file;
        const isPV = selectedFiles.includes(sourceFile);
        const fileName = isPV ? `P${code}-PV-${outputName}.pdf` : `P${code}-${outputName}.pdf`;
        
        if (!structure[code].files[fileName]) {
          structure[code].files[fileName] = {
            name: fileName,
            pages: [],
            isPV: isPV
          };
        }
        
        structure[code].files[fileName].pages.push({
          pageNumber: page.page_number,
          sourceFile: page.source_file,
          isMain: page.is_main
        });
      });
    });
    
    setFinalStructure(structure);
    setShowFolderPreview(true);
  };

  const handleFinalMerge = async () => {
    if (Object.keys(codeGroups).length === 0) {
      toast.error('❌ Aucune donnée à fusionner');
      return;
    }

    setMerging(true);
    try {
      const mergeData = {
        code_groups: Object.entries(codeGroups)
          .filter(([code]) => code !== 'NO_CODE')
          .map(([code, groupPages]) => ({
            code,
            pages: groupPages.map(p => ({
              page_id: p.page_id,
              page_number: p.page_number,
              code: p.code,
              output_name: p.output_name || 'DEFAULT',
              source_file: p.source_file,
              is_main: p.is_main ?? true,
              is_child: p.is_child ?? false,
              original_file_path: p.original_file_path,
              original_page_number: p.original_page_number || 0
            })),
            output_names: [...new Set(groupPages.map(p => p.output_name || 'DEFAULT'))],
            merged_files: selectedFiles
          }))
      };

      const response = await axios.post(
        `${BACKEND_URL}/api/session/${sessionId}/merge-final`,
        mergeData
      );

      if (response.data.success) {
        toast.success(`✅ ${response.data.files.length} fichier(s) créé(s)!`);
        setShowFinalSummary(true);
        previewFinalStructure();
      } else {
        toast.error('❌ Erreur lors de la fusion');
      }
    } catch (error) {
      toast.error('❌ Erreur lors de la fusion finale');
    } finally {
      setMerging(false);
    }
  };

  const downloadZip = async () => {
    try {
      toast.info('📦 Création du ZIP...');
      const response = await axios.get(
        `${BACKEND_URL}/api/session/${sessionId}/download-zip`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `scanflow_${sessionId.slice(0, 8)}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('✅ ZIP téléchargé!');
    } catch (error) {
      toast.error('❌ Erreur téléchargement');
    }
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const uniqueCodes = ['all', ...new Set(pages.map(p => p.code).filter(Boolean))];
  const uniqueSourceFiles = ['all', ...new Set(pages.map(p => p.source_file).filter(Boolean))];
  const uniqueOutputNames = ['all', ...new Set(pages.map(p => p.output_name).filter(Boolean))];
  
  const filteredAndSortedPages = pages
    .filter(page => {
      const matchesSearch = !searchTerm || 
        page.code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        page.source_file?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        page.output_name?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesCode = filterCode === 'all' || page.code === filterCode;
      const matchesSourceFile = filterSourceFile === 'all' || page.source_file === filterSourceFile;
      const matchesOutputName = filterOutputName === 'all' || page.output_name === filterOutputName;
      
      return matchesSearch && matchesCode && matchesSourceFile && matchesOutputName;
    })
    .sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (sortField === 'page_number' || sortField === 'confidence') {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      } else {
        aVal = String(aVal || '').toLowerCase();
        bVal = String(bVal || '').toLowerCase();
      }
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

  const validCodes = Object.keys(codeGroups).filter(code => code !== 'NO_CODE');

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-slate-400 text-lg">Chargement...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <img 
              src="/logo.png" 
              alt="ScanFlow Pro Logo" 
              className="w-12 h-12 object-contain"
            />
            <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-600">
              Résultats et Vérification
            </h1>
          </div>
          
          <div className="flex gap-3">
            <Button
              onClick={() => navigate('/')}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-800"
            >
              <Home className="w-4 h-4 mr-2" />
              Accueil
            </Button>
            <Button
              onClick={() => navigate(`/analysis/${sessionId}`)}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-800"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Analyse
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-indigo-500/20 to-indigo-600/20 border-2 border-indigo-500/30 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-indigo-300 mb-1">Total Pages</p>
                <p className="text-3xl font-bold text-white">{pages.length}</p>
              </div>
              <FileText className="w-12 h-12 text-indigo-400 opacity-50" />
            </div>
          </Card>
          
          <Card className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 border-2 border-emerald-500/30 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-emerald-300 mb-1">Codes Valides</p>
                <p className="text-3xl font-bold text-white">{validCodes.length}</p>
              </div>
              <CheckCircle className="w-12 h-12 text-emerald-400 opacity-50" />
            </div>
          </Card>
          
          <Card className="bg-gradient-to-br from-amber-500/20 to-amber-600/20 border-2 border-amber-500/30 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-amber-300 mb-1">Fichiers</p>
                <p className="text-3xl font-bold text-white">{new Set(pages.map(p => p.source_file)).size}</p>
              </div>
              <Package className="w-12 h-12 text-amber-400 opacity-50" />
            </div>
          </Card>
          
          <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 border-2 border-purple-500/30 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-purple-300 mb-1">Confiance</p>
                <p className="text-3xl font-bold text-white">
                  {pages.length > 0 ? Math.round((pages.reduce((sum, p) => sum + (p.confidence || 0), 0) / pages.length) * 100) : 0}%
                </p>
              </div>
              <Eye className="w-12 h-12 text-purple-400 opacity-50" />
            </div>
          </Card>
        </div>

        <Card className="mb-6 bg-slate-900/90 border-2 border-slate-700 p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <Label className="text-slate-300 mb-2 block">🔍 Recherche</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <Input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Code, fichier..."
                  className="pl-10 bg-slate-800/50 border-slate-600 text-slate-100"
                />
              </div>
            </div>
            
            <div>
              <Label className="text-slate-300 mb-2 block">🏷️ Code</Label>
              <Select value={filterCode} onValueChange={setFilterCode}>
                <SelectTrigger className="bg-slate-800/50 border-slate-600 text-slate-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {uniqueCodes.map(code => (
                    <SelectItem key={code} value={code}>
                      {code === 'all' ? 'Tous' : code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-slate-300 mb-2 block">📁 Fichier</Label>
              <Select value={filterSourceFile} onValueChange={setFilterSourceFile}>
                <SelectTrigger className="bg-slate-800/50 border-slate-600 text-slate-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {uniqueSourceFiles.map(file => (
                    <SelectItem key={file} value={file}>
                      {file === 'all' ? 'Tous' : file}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-slate-300 mb-2 block">📄 Nom</Label>
              <Select value={filterOutputName} onValueChange={setFilterOutputName}>
                <SelectTrigger className="bg-slate-800/50 border-slate-600 text-slate-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {uniqueOutputNames.map(name => (
                    <SelectItem key={name} value={name}>
                      {name === 'all' ? 'Tous' : name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap">
            <Button onClick={previewFinalStructure} className="bg-blue-600 hover:bg-blue-700" disabled={validCodes.length === 0}>
              <FolderOpen className="w-4 h-4 mr-2" />
              Prévisualiser
            </Button>
            
            <Button onClick={() => setShowMergeSettings(true)} className="bg-indigo-600 hover:bg-indigo-700" disabled={validCodes.length === 0}>
              <Package className="w-4 h-4 mr-2" />
              Configurer Fusion
            </Button>

            <Button onClick={handleFinalMerge} className="bg-emerald-600 hover:bg-emerald-700" disabled={validCodes.length === 0 || merging}>
              <Save className="w-4 h-4 mr-2" />
              {merging ? 'Fusion...' : 'Créer Fichiers'}
            </Button>

            <Button onClick={downloadZip} variant="outline" className="border-emerald-600 text-emerald-400">
              <Download className="w-4 h-4 mr-2" />
              ZIP
            </Button>

            <Button onClick={clearCache} variant="outline" className="border-amber-600 text-amber-400">
              <Database className="w-4 h-4 mr-2" />
              Cache
            </Button>

            <Button onClick={clearOldFiles} variant="outline" className="border-red-600 text-red-400">
              <Trash className="w-4 h-4 mr-2" />
              Vieux
            </Button>

            <Button onClick={() => fetchResults()} variant="outline" className="border-blue-600 text-blue-400">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualiser
            </Button>
          </div>
        </Card>

        <Card className="bg-slate-900/90 border-2 border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-800/90 border-b-2 border-slate-700">
                <tr>
                  <th className="px-4 py-4 text-left">
                    <button onClick={() => handleSort('page_number')} className="flex items-center gap-2 text-sm font-bold text-slate-200 hover:text-indigo-400">
                      Page
                      {sortField === 'page_number' && (sortDirection === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />)}
                    </button>
                  </th>
                  <th className="px-4 py-4 text-left">
                    <button onClick={() => handleSort('code')} className="flex items-center gap-2 text-sm font-bold text-slate-200 hover:text-indigo-400">
                      Code
                      {sortField === 'code' && (sortDirection === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />)}
                    </button>
                  </th>
                  <th className="px-4 py-4 text-left">Confiance</th>
                  <th className="px-4 py-4 text-left">Type</th>
                  <th className="px-4 py-4 text-left">Nom</th>
                  <th className="px-4 py-4 text-left">Fichier</th>
                  <th className="px-4 py-4 text-left">ROI</th>
                  <th className="px-4 py-4 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedPages.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-4 py-12 text-center text-slate-400">
                      Aucun résultat
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedPages.map((page, index) => (
                    <tr key={page.page_id} className="border-b border-slate-800 hover:bg-slate-800/50">
                      <td className="px-4 py-3 text-slate-300 font-semibold">{page.page_number}</td>
                      <td className="px-4 py-3">
                        {editingCell === `${page.page_id}-code` ? (
                          <Input
                            value={page.code || ''}
                            onChange={(e) => {
                              setPages(prev => prev.map(p => 
                                p.page_id === page.page_id ? { ...p, code: e.target.value } : p
                              ));
                            }}
                            onBlur={() => {
                              updatePage(page.page_id, 'code', page.code);
                              setEditingCell(null);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                updatePage(page.page_id, 'code', page.code);
                                setEditingCell(null);
                              }
                            }}
                            className="h-8 bg-slate-800 border-indigo-500 w-32"
                            autoFocus
                          />
                        ) : (
                          <div onClick={() => setEditingCell(`${page.page_id}-code`)} className="font-bold text-indigo-400 cursor-pointer hover:underline">
                            {page.code || 'N/A'}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          (page.confidence || 0) > 0.8 ? 'bg-emerald-500/20 text-emerald-400' :
                          (page.confidence || 0) > 0.5 ? 'bg-amber-500/20 text-amber-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {Math.round((page.confidence || 0) * 100)}%
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {page.is_main ? (
                          <span className="px-2 py-1 rounded text-xs font-bold bg-indigo-500/20 text-indigo-400">
                            Main
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded text-xs font-bold bg-slate-700/20 text-slate-400">
                            Child
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-medium">{page.output_name || 'DEFAULT'}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs">{page.source_file}</td>
                      <td className="px-4 py-3">
                        {page.code_image_url ? (
                          <Button size="sm" variant="ghost" onClick={() => window.open(`${BACKEND_URL}${page.code_image_url}`, '_blank')} className="text-blue-400 hover:text-blue-300">
                            <Eye className="w-4 h-4" />
                          </Button>
                        ) : (
                          <span className="text-xs text-slate-600">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => handleReorderPage(page.page_id, 'up')} className="text-slate-400 hover:text-slate-300" title="Monter">
                            <ArrowUp className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleReorderPage(page.page_id, 'down')} className="text-slate-400 hover:text-slate-300" title="Descendre">
                            <ArrowDown className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => { setSelectedPage(page); setShowMoveModal(true); }} className="text-blue-400 hover:text-blue-300" title="Déplacer">
                            <Move className="w-4 h-4" />
                          </Button>
                          {page.decision_log && page.decision_log.length > 0 && (
                            <Button size="sm" variant="ghost" onClick={() => showDecisionLogModal(page)} className="text-purple-400 hover:text-purple-300" title="Log">
                              <Info className="w-4 h-4" />
                            </Button>
                          )}
                          <Button size="sm" variant="ghost" onClick={() => deletePage(page.page_id)} className="text-red-400 hover:text-red-300" title="Supprimer">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          <div className="px-6 py-4 bg-slate-800/50 border-t border-slate-700">
            <p className="text-sm text-slate-400">
              Affichage de {filteredAndSortedPages.length} sur {pages.length} page(s)
            </p>
          </div>
        </Card>

        {/* Modal Déplacer Page */}
        {showMoveModal && selectedPage && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowMoveModal(false)}>
            <div className="bg-slate-900 border-2 border-indigo-500 rounded-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-xl font-bold text-indigo-400 mb-4">Déplacer la page</h3>
              <p className="text-slate-300 mb-4">Page {selectedPage.page_number} - Code actuel: {selectedPage.code}</p>
              <Label className="text-slate-200 mb-2 block">Nouveau code:</Label>
              <Input
                value={moveToCode}
                onChange={(e) => setMoveToCode(e.target.value)}
                placeholder="Entrez le code"
                className="bg-slate-800 border-slate-600 text-slate-100 mb-4"
              />
              <div className="flex gap-3">
                <Button onClick={handleMovePage} className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                  Déplacer
                </Button>
                <Button onClick={() => setShowMoveModal(false)} variant="outline" className="border-slate-600">
                  Annuler
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal Decision Log */}
        {showDecisionLog && selectedPage && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowDecisionLog(false)}>
            <div className="bg-slate-900 border-2 border-purple-500 rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-auto p-6" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-2xl font-bold text-purple-400 mb-4">📋 Decision Log - Page {selectedPage.page_number}</h3>
              {selectedPage.recovery_used && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-4">
                  <p className="text-amber-300">⚠️ Auto-Recovery utilisé pour cette page</p>
                </div>
              )}
              <div className="space-y-3">
                {selectedPage.decision_log && selectedPage.decision_log.map((log, idx) => (
                  <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                    <div className="font-bold text-indigo-400 mb-2">Stratégie: {log.strategy}</div>
                    {log.result && (
                      <div className="text-sm text-slate-300 space-y-1">
                        <div>Code: {log.result.code || 'N/A'}</div>
                        <div>Confiance: {Math.round((log.result.confidence || 0) * 100)}%</div>
                        <div>Méthode: {log.result.method}</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <Button onClick={() => setShowDecisionLog(false)} className="w-full mt-4 bg-purple-600 hover:bg-purple-700">
                Fermer
              </Button>
            </div>
          </div>
        )}

        {/* Autres modals existants... */}
        {showMergeSettings && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowMergeSettings(false)}>
            <div className="bg-slate-900 border-2 border-indigo-500 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-auto p-8" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-indigo-400 mb-6">
                ⚙️ Configuration Fusion
              </h2>
              
              <Label className="text-slate-200 text-lg font-bold mb-4 block">Fichiers PV:</Label>
              <div className="space-y-2 max-h-60 overflow-auto mb-6">
                {[...new Set(pages.map(p => p.source_file))].map(fileName => (
                  <div key={fileName} className="flex items-center space-x-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800">
                    <Checkbox
                      id={fileName}
                      checked={selectedFiles.includes(fileName)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedFiles([...selectedFiles, fileName]);
                        } else {
                          setSelectedFiles(selectedFiles.filter(f => f !== fileName));
                        }
                      }}
                    />
                    <label htmlFor={fileName} className="text-slate-300 cursor-pointer flex-1">
                      {fileName}
                    </label>
                  </div>
                ))}
              </div>
              
              <div className="flex gap-4">
                <Button onClick={() => { setShowMergeSettings(false); toast.success('✅ Configuration sauvegardée'); }} className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                  Sauvegarder
                </Button>
                <Button variant="outline" onClick={() => setShowMergeSettings(false)} className="border-slate-600">
                  Annuler
                </Button>
              </div>
            </div>
          </div>
        )}

        {showFolderPreview && finalStructure && (
          <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowFolderPreview(false)}>
            <div className="bg-slate-900 border-2 border-indigo-500 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-auto p-8" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-3xl font-bold text-indigo-400 mb-6">📁 Prévisualisation Structure</h2>
              <div className="space-y-6">
                {Object.entries(finalStructure).map(([code, data]) => (
                  <Card key={code} className="bg-slate-800/50 border-2 border-slate-700 p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <Folder className="w-8 h-8 text-amber-400" />
                      <h3 className="text-2xl font-bold text-amber-400">{data.folder}/</h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 ml-8">
                      {Object.entries(data.files).map(([fileName, fileData]) => (
                        <div key={fileName} className="bg-slate-900/70 border border-slate-700 rounded-lg p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <FileText className={`w-5 h-5 ${fileData.isPV ? 'text-purple-400' : 'text-emerald-400'}`} />
                            <div className="font-bold text-slate-100 text-sm">{fileName}</div>
                          </div>
                          <div className="text-xs text-slate-400">{fileData.pages.length} page(s)</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
              <Button onClick={() => setShowFolderPreview(false)} className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700">
                Fermer
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Results;
