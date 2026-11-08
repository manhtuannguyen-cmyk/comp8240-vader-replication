"""Mock SDK adapters only: these tests never call a provider or spend tokens."""
import importlib.util
import unittest
from unittest.mock import MagicMock,patch
from src.llm_judge.run_judges import call_provider


def installed(module):
    try:return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:return False


class OptionalAPITests(unittest.TestCase):
    @unittest.skipUnless(installed('openai'),'optional OpenAI SDK not installed')
    def test_openai_public_text_and_request(self):
        response=MagicMock();response.model_dump.return_value={'id':'test'};response.output_text='{}'
        with patch.dict('os.environ',{'OPENAI_API_KEY':'unit-test-only'}),patch('openai.OpenAI') as client:
            client.return_value.responses.create.return_value=response
            raw,text=call_provider('openai','explicit-model','only input text',None,None,100)
            args=client.return_value.responses.create.call_args.kwargs
            self.assertEqual(args['input'],'only input text');self.assertFalse(args['store'])
            self.assertNotIn('temperature',args);self.assertEqual(text,'{}')

    @unittest.skipUnless(installed('anthropic'),'optional Anthropic SDK not installed')
    def test_anthropic_public_text_and_no_invented_system_prompt(self):
        block=MagicMock();block.type='text';block.text='{}'
        response=MagicMock();response.content=[block];response.model_dump.return_value={'id':'test'}
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'unit-test-only'}),patch('anthropic.Anthropic') as client:
            client.return_value.messages.create.return_value=response
            raw,text=call_provider('anthropic','explicit-model','only input text',None,.2,100)
            args=client.return_value.messages.create.call_args.kwargs
            self.assertNotIn('system',args);self.assertEqual(args['messages'],[{'role':'user','content':'only input text'}])
            self.assertEqual(text,'{}')

    @unittest.skipUnless(installed('google.genai'),'optional Google SDK not installed')
    def test_google_json_configuration(self):
        response=MagicMock();response.text='{}';response.model_dump.return_value={'candidates':[]}
        with patch.dict('os.environ',{'GEMINI_API_KEY':'unit-test-only'}),patch('google.genai.Client') as client:
            client.return_value.models.generate_content.return_value=response
            raw,text=call_provider('google','explicit-model','only input text',None,None,100)
            args=client.return_value.models.generate_content.call_args.kwargs
            self.assertEqual(args['contents'],'only input text')
            self.assertEqual(args['config'].response_mime_type,'application/json')
            self.assertEqual(text,'{}')


if __name__=='__main__':unittest.main()
