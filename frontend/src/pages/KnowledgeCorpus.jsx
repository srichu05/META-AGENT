import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApp } from '../context/AppContext';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import {
  Database,
  UploadCloud,
  FileText,
  CheckCircle2,
  Search,
  RotateCw,
  FolderOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Layers,
  Filter,
} from 'lucide-react';
import { MOCK_CORPUS_DATA } from '../utils/mockData';

export const KnowledgeCorpus = () => {
  const { addToast, executeGetCorpus, executeUploadCorpus } = useApp();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState(null);

  const [corpusData, setCorpusData] = useState(MOCK_CORPUS_DATA);
  const [corpusCount, setCorpusCount] = useState(MOCK_CORPUS_DATA.length);
  const [isLoadingCorpus, setIsLoadingCorpus] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [expandedIndex, setExpandedIndex] = useState(0); // expand first by default

  const fetchCorpus = async () => {
    setIsLoadingCorpus(true);
    try {
      const res = await executeGetCorpus();
      const count = res?.count || res?.problems?.length || MOCK_CORPUS_DATA.length;
      const problems = res?.problems || MOCK_CORPUS_DATA;
      setCorpusCount(count);
      setCorpusData(problems);
    } catch (err) {
      console.error('Corpus fetch error:', err);
      setCorpusData(MOCK_CORPUS_DATA);
      setCorpusCount(MOCK_CORPUS_DATA.length);
    } finally {
      setIsLoadingCorpus(false);
    }
  };

  useEffect(() => {
    fetchCorpus();
  }, []);

  const handleFileSelect = (file) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith('.json') && !name.endsWith('.jsonl')) {
      addToast('Please upload a valid .json or .jsonl dataset file', 'warning');
      return;
    }
    setSelectedFile(file);
    setUploadStatus(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      addToast('Please select a JSON or JSONL file to upload', 'warning');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadStatus(null);

    try {
      const res = await executeUploadCorpus(selectedFile, (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        }
      });

      const message = res?.message || `Successfully indexed ${res?.count || 'corpus'} problems into RAG vector store`;
      setUploadStatus(message);
      addToast(message, 'success', 'Corpus Indexed');
      setSelectedFile(null);
      fetchCorpus();
    } catch (err) {
      console.error('Upload error:', err);
      addToast(err.message || 'Upload failed', 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleLoadSampleDataset = () => {
    setCorpusData(MOCK_CORPUS_DATA);
    setCorpusCount(MOCK_CORPUS_DATA.length);
    addToast('Loaded GSM8K curated benchmark dataset', 'success');
  };

  const categories = ['All', 'Arithmetic', 'Algebra', 'Geometry', 'Number Theory', 'Fractions'];

  const filteredProblems = corpusData.filter((item) => {
    const prob = typeof item === 'string' ? item : item.problem || item.question || '';
    const ans = typeof item === 'object' ? item.answer || item.solution || '' : '';
    const type = typeof item === 'object' ? item.type || '' : '';

    const matchesSearch =
      !searchQuery.trim() ||
      prob.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ans.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory =
      categoryFilter === 'All' || type.toLowerCase().includes(categoryFilter.toLowerCase());

    return matchesSearch && matchesCategory;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Description */}
      <div>
        <h2 style={{ fontSize: '1.45rem' }}>Knowledge Base & RAG Vector Store Management</h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Ingest structured GSM8K or Olympiad datasets (.json / .jsonl) to re-index the RAG vector store dynamically.
        </p>
      </div>

      {/* Upload Zone Card */}
      <Card
        title="Upload & Ingest Knowledge Corpus"
        subtitle="Accepts structured datasets (.json or .jsonl). Generates local dense embeddings for retrieval."
        icon={UploadCloud}
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={Sparkles}
            onClick={handleLoadSampleDataset}
          >
            Load GSM8K Benchmark
          </Button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Drag & Drop Container */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? 'var(--accent-cobalt)' : 'var(--border-default)'}`,
              borderRadius: 'var(--radius-lg)',
              backgroundColor: isDragging ? 'var(--accent-cobalt-subtle)' : 'var(--bg-subtle)',
              padding: '36px 24px',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all var(--transition-normal)',
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".json,.jsonl"
              style={{ display: 'none' }}
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />

            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-default)',
                color: 'var(--accent-cobalt)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 14px auto',
                boxShadow: 'var(--shadow-subtle)',
              }}
            >
              <UploadCloud size={24} />
            </div>

            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '1rem',
                color: 'var(--text-primary)',
                marginBottom: '4px',
              }}
            >
              {selectedFile ? selectedFile.name : 'Choose a dataset file or drag and drop here'}
            </div>

            <div style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
              {selectedFile
                ? `${(selectedFile.size / 1024).toFixed(1)} KB selected`
                : 'JSON or JSONL format (supports GSM8K problem, question, solution & answer fields)'}
            </div>
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              {selectedFile && (
                <Badge variant="sage" size="md" icon={FileText}>
                  Ready to index: {selectedFile.name}
                </Badge>
              )}
            </div>

            <Button
              variant="electric"
              size="md"
              icon={Database}
              isLoading={isUploading}
              loadingText={`Indexing (${uploadProgress}%)...`}
              onClick={handleUpload}
              disabled={isUploading || !selectedFile}
            >
              Upload & Index Corpus
            </Button>
          </div>

          {/* Progress Bar */}
          {isUploading && (
            <div style={{ width: '100%' }}>
              <div
                style={{
                  height: '6px',
                  backgroundColor: 'var(--border-subtle)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    backgroundColor: 'var(--accent-cobalt)',
                    transition: 'width 0.2s ease',
                  }}
                />
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                  marginTop: '4px',
                }}
              >
                <span>Generating Dense Vector Embeddings</span>
                <span>{uploadProgress}%</span>
              </div>
            </div>
          )}

          {/* Success Status Alert */}
          {uploadStatus && (
            <div
              style={{
                padding: '16px 20px',
                backgroundColor: 'var(--status-success-bg)',
                border: '1px solid #86EFAC',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                color: 'var(--status-success)',
              }}
            >
              <CheckCircle2 size={20} />
              <div style={{ fontSize: '0.9rem' }}>{uploadStatus}</div>
            </div>
          )}
        </div>
      </Card>

      {/* Active Corpus Dataset Preview Section */}
      <Card
        title={`Active Corpus Preview (${corpusCount} Items Synchronized)`}
        subtitle="Live mathematical problems indexed in the dense vector space."
        icon={Database}
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={RotateCw}
            isLoading={isLoadingCorpus}
            loadingText="Loading..."
            onClick={fetchCorpus}
          >
            Refresh List
          </Button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Category Filter Pills & Search */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  style={{
                    fontSize: '0.8rem',
                    fontFamily: 'var(--font-mono)',
                    padding: '4px 12px',
                    borderRadius: 'var(--radius-full)',
                    border: categoryFilter === cat ? '1px solid var(--accent-cobalt)' : '1px solid var(--border-default)',
                    backgroundColor: categoryFilter === cat ? 'var(--accent-cobalt-subtle)' : 'var(--bg-card)',
                    color: categoryFilter === cat ? 'var(--accent-cobalt)' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontWeight: categoryFilter === cat ? 600 : 500,
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Search Bar */}
            <div style={{ position: 'relative', width: '280px' }}>
              <Search
                size={14}
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)',
                }}
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search problem text..."
                style={{
                  width: '100%',
                  padding: '8px 12px 8px 34px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-default)',
                  backgroundColor: 'var(--bg-subtle)',
                  fontSize: '0.85rem',
                  fontFamily: 'var(--font-body)',
                }}
              />
            </div>
          </div>

          {/* List of Problems */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              maxHeight: '440px',
              overflowY: 'auto',
              paddingRight: '6px',
            }}
          >
            {filteredProblems.map((item, idx) => {
              const problemText = typeof item === 'string' ? item : item.problem || item.question || 'Untitled Problem';
              const answerText = typeof item === 'object' ? item.answer : '';
              const solutionText = typeof item === 'object' ? item.solution : '';
              const difficulty = typeof item === 'object' ? item.difficulty : 'Introductory';
              const pType = typeof item === 'object' ? item.type : 'General';
              const isExpanded = expandedIndex === idx;

              return (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px 18px',
                    cursor: 'pointer',
                    transition: 'border-color var(--transition-fast)',
                    boxShadow: 'var(--shadow-subtle)',
                  }}
                  onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <span
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            color: 'var(--accent-cobalt)',
                          }}
                        >
                          #{idx + 1}
                        </span>
                        {pType && (
                          <Badge variant="sky" size="sm">
                            {pType}
                          </Badge>
                        )}
                        {difficulty && (
                          <Badge variant="lemon" size="sm">
                            {difficulty}
                          </Badge>
                        )}
                      </div>

                      <div
                        style={{
                          fontSize: '0.925rem',
                          color: 'var(--text-primary)',
                          lineHeight: 1.5,
                          fontFamily: 'var(--font-body)',
                        }}
                      >
                        {problemText}
                      </div>
                    </div>

                    <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </div>
                  </div>

                  {/* Expanded Solution / Answer Drawer */}
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      style={{
                        marginTop: '12px',
                        paddingTop: '12px',
                        borderTop: '1px dashed var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }}
                    >
                      {answerText && (
                        <div style={{ fontSize: '0.85rem' }}>
                          <strong style={{ color: 'var(--accent-cobalt)', fontFamily: 'var(--font-mono)' }}>
                            Ground Truth Answer:
                          </strong>{' '}
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{answerText}</span>
                        </div>
                      )}
                      {solutionText && (
                        <div
                          style={{
                            fontSize: '0.825rem',
                            color: 'var(--text-secondary)',
                            backgroundColor: 'var(--bg-canvas)',
                            padding: '12px 16px',
                            borderRadius: 'var(--radius-sm)',
                            fontFamily: 'var(--font-mono)',
                            lineHeight: 1.55,
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {solutionText}
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default KnowledgeCorpus;
