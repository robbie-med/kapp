const AudioCapture = {
    mediaRecorder: null,
    chunks: [],
    stream: null,

    async start() {
        this.chunks = [];
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaRecorder = new MediaRecorder(this.stream, {
            mimeType: this._getSupportedMime(),
        });
        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.chunks.push(e.data);
        };
        this.mediaRecorder.start();
    },

    stop() {
        return new Promise((resolve) => {
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.chunks, { type: this.mediaRecorder.mimeType });
                this._cleanup();
                resolve(blob);
            };
            this.mediaRecorder.stop();
        });
    },

    _cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
    },

    _getSupportedMime() {
        const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) return type;
        }
        return '';
    },

    getExtension() {
        const mime = this._getSupportedMime();
        if (mime.includes('webm')) return 'webm';
        if (mime.includes('ogg')) return 'ogg';
        if (mime.includes('mp4')) return 'mp4';
        return 'webm';
    },
};
