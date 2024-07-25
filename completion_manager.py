from config_loader import config
import re
from utils import to_clipboard, maintain_token_limit

class CompletionManager:
    def __init__(self, verbose=False):
        """Initialize the CompletionManager with the TTS client."""
        self.client = None
        self.model = None
        self.verbose = verbose
        self._setup_client()

    def _setup_client(self):
        """Instantiates the appropriate AI client based on configuration file."""
        if config.COMPLETIONS_API == "openai":
            from llm_apis.openai_client import OpenAIClient
            self.client = OpenAIClient(verbose=self.verbose)
            
        elif config.COMPLETIONS_API == "together":
            from llm_apis.togetherai_client import TogetherAIClient
            self.client = TogetherAIClient(verbose=self.verbose)

        elif config.COMPLETIONS_API == "anthropic":
            from llm_apis.anthropic_client import AnthropicClient
            self.client = AnthropicClient(verbose=self.verbose)

        elif config.COMPLETIONS_API == "perplexity":
            from llm_apis.perplexity_client import PerplexityClient
            self.client = PerplexityClient(verbose=self.verbose)

        elif config.COMPLETIONS_API == "openrouter":
            from llm_apis.openrouter_client import OpenRouterClient
            self.client = OpenRouterClient(verbose=self.verbose)
        
        elif config.COMPLETIONS_API == "groq":
            from llm_apis.groq_client import GroqClient
            self.client = GroqClient(verbose=self.verbose)

        elif config.COMPLETIONS_API == "lm_studio":
            from llm_apis.lm_studio_client import LM_StudioClient
            if hasattr(config, 'LM_STUDIO_API_BASE_URL'):
                self.client = LM_StudioClient(base_url=config.LM_STUDIO_API_BASE_URL, verbose=self.verbose)
            else:
                print("No LM_STUDIO_API_BASE_URL found in config.py, using default")
                self.client = LM_StudioClient(verbose=self.verbose)

        elif config.COMPLETIONS_API == "ollama":
            from llm_apis.ollama_client import OllamaClient
            if hasattr(config, 'OLLAMA_API_BASE_URL'):
                self.client = OllamaClient(base_url=config.OLLAMA_API_BASE_URL, verbose=self.verbose)
                
            else:
                print("No OLLAMA_API_BASE_URL found in config.py, using default")
                self.client = OllamaClient(verbose=self.verbose)
        else:
            raise ValueError("Unsupported completion API service configured")
        
    def get_completion(self, messages, model, **kwargs):
        """Get completion from the selected AI client and stream sentences into the TTS client.

        Args:
            messages (list): List of messages.
            model (str): Model for completion.
            **kwargs: Additional keyword arguments.

        Returns:
            generator: Stream of sentences or clipboard text chunks generated by the AI client, 
                    or None if an error occurs.
        """
        try:
            # Make sure the token count is within the limit
            messages = maintain_token_limit(messages, config.MAX_TOKENS)
            
            direct_stream = self.client.stream_completion(messages, model, **kwargs)
            stream = self._stream_sentences_from_chunks(direct_stream, clip_start_marker=config.START_SEQ, clip_end_marker=config.END_SEQ)

            return stream

        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            else:
                print(f"An error occurred while getting completion: {e}")
            return None
        
    def _stream_sentences_from_chunks(self, chunks_stream, clip_start_marker="-CLIPSTART-", clip_end_marker="-CLIPEND-"):
        """
        Takes in audio chunks and returns sentences or chunks of text for the clipboard, as well as the full unmodified text stream.
        Supports both clip markers and triple backticks for marking clipboard text.

        Args:
            chunks_stream: Stream of chunks.
            clip_start_marker (str): Start marker for clipboard text using clip markers.
            clip_end_marker (str): End marker for clipboard text using clip markers.

        Yields:
            tuple: Type of content ("sentence" or "clipboard_text") and the content itself.
        """
        buffer = ''
        full_response = ''
        sentence_endings = re.compile(r'(?<=[.!?])\s+|(?<=\n)')
        in_marker = False
        in_backticks = False

        for chunk in chunks_stream:
            buffer += chunk
            full_response += chunk

            if not in_backticks:
                if clip_start_marker in buffer and not in_marker:
                    pre, match, post = buffer.partition(clip_start_marker)
                    if pre.strip():
                        yield "sentence", pre.strip()
                    buffer = post
                    in_marker = True

                if clip_end_marker in buffer and in_marker:
                    marked_section, _, post_end = buffer.partition(clip_end_marker)
                    yield "clipboard_text", marked_section.strip()
                    buffer = post_end
                    in_marker = False

            if not in_marker:
                if not in_backticks and '```' in buffer:
                    pre, _, post = buffer.partition('```')
                    if pre.strip():
                        yield "sentence", pre.strip()
                    buffer = post
                    in_backticks = True
                elif in_backticks and '```' in buffer:
                    marked_section, _, post_end = buffer.partition('```')
                    yield "clipboard_text", '```' + marked_section.strip() + '```'
                    yield "sentence", "Code saved to the clipboard."
                    buffer = post_end
                    in_backticks = False

            if not in_marker and not in_backticks:
                while True:
                    match = sentence_endings.search(buffer)
                    if match:
                        sentence = buffer[:match.end()]
                        buffer = buffer[match.end():]
                        if sentence.strip():
                            yield "sentence", sentence.strip()
                    else:
                        break

        if buffer.strip():
            if in_backticks:
                yield "clipboard_text", '```' + buffer.strip()
            elif not in_marker:
                yield "sentence", buffer.strip()
            else:
                yield "clipboard_text", buffer.strip()

        if full_response.strip():
            yield "full_response", full_response.strip()
            