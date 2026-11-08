"""Tests target errors that would change research conclusions or leak labels."""
import unittest
import numpy as np
from sklearn.metrics import cohen_kappa_score, f1_score
from src.evaluation.metrics import vader_polarity,human_polarity,fast_class,bootstrap_indices,ccc
from src.llm_judge.parse_responses import normalize,validate_predictions,parse_text
from src.annotation.agreement import weighted_kappa
from src.data_processing.map_goemotions import map_emotions


class ReproducibilityTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(list(vader_polarity([-.05,-.04999,0,.04999,.05])),['negative','neutral','neutral','neutral','positive'])
        self.assertEqual(list(human_polarity([-1,0,1])),['negative','neutral','positive'])
        with self.assertRaises(ValueError):human_polarity([np.nan])

    def test_missing_score_is_not_neutral(self):
        record={'sample_id':'COM001','sentiment_score':'','sentiment_label':'neutral','confidence':.5,'uncertain':True,'justification':'uncertain'}
        with self.assertRaises(ValueError):normalize(record)

    def test_llm_score_and_label_must_agree(self):
        record={'sample_id':'COM001','sentiment_score':2,'sentiment_label':'negative','confidence':.9,'uncertain':False,'justification':'test'}
        with self.assertRaises(ValueError):normalize(record)
        record.update(sentiment_label='positive',sentiment_score=True)
        with self.assertRaises(ValueError):normalize(record)

    def test_id_alignment_not_row_order(self):
        make=lambda sid:{'sample_id':sid,'sentiment_score':0,'sentiment_label':'neutral','confidence':.5,'uncertain':True,'justification':'test'}
        result=validate_predictions([make('B'),make('A')],['A','B'])
        self.assertEqual(result.sample_id.tolist(),['A','B'])
        with self.assertRaises(ValueError):validate_predictions([make('A'),make('A')],['A','B'])

    def test_json_fences_and_boolean(self):
        records=parse_text('```json\n{"sample_id":"A","sentiment_score":0,"sentiment_label":"neutral","confidence":0.5,"uncertain":true,"justification":"test"}\n```')
        self.assertTrue(normalize(records[0])['uncertain'])

    def test_metric_implementation_matches_sklearn(self):
        rng=np.random.default_rng(8240)
        a,b=rng.integers(0,3,200),rng.integers(0,3,200)
        acc,f1,k=fast_class(a,b)
        self.assertAlmostEqual(f1,f1_score(a,b,labels=[0,1,2],average='macro'))
        self.assertAlmostEqual(k,cohen_kappa_score(a,b,labels=[0,1,2]))
        self.assertAlmostEqual(acc,float(np.mean(a==b)))

    def test_ordinal_kappa_implementation(self):
        rng=np.random.default_rng(42);a,b=rng.integers(-4,5,100),rng.integers(-4,5,100)
        self.assertAlmostEqual(weighted_kappa(a,b),cohen_kappa_score(a,b,labels=list(range(-4,5)),weights='quadratic'))

    def test_bootstrap_preserves_source_allocations_and_pairs(self):
        groups=np.array(['video1']*3+['video2']*4)
        a=bootstrap_indices(7,groups,repetitions=10)
        self.assertTrue(np.array_equal(a,bootstrap_indices(7,groups,repetitions=10)))
        self.assertTrue(np.all((a[:,:3]<3)))
        self.assertTrue(np.all((a[:,3:]>=3)))

    def test_concordance_is_not_correlation(self):
        self.assertAlmostEqual(ccc([0,1,2],[0,1,2]),1)
        self.assertLess(ccc([0,1,2],[1,2,3]),1)

    def test_ambiguous_and_mixed_emotions_excluded(self):
        mapping={'positive':['joy'],'negative':['anger'],'neutral':['neutral'],'ambiguous':['surprise']}
        self.assertEqual(map_emotions(['joy'],mapping),('positive',[]))
        self.assertEqual(map_emotions(['joy','anger'],mapping)[0],'')
        self.assertEqual(map_emotions(['neutral','joy'],mapping)[0],'')
        self.assertEqual(map_emotions(['surprise'],mapping)[0],'')


if __name__=='__main__':unittest.main()
