#! /usr/bin/env python
import yaml
import hashlib
import sourmash_lib

class SourmashSignature(object):
    def __init__(self, email, estimator, name='', filename=''):
        self.d = {}
        self.d['class'] = 'sourmash_signature'
        self.d['type'] = 'mrnaseq'
        self.d['email'] = email
        if name:
            self.d['name'] = name
        if filename:
            self.d['filename'] = filename
        
        self.estimator = estimator

    def md5sum(self):
        m = hashlib.md5()
        for k in self.estimator._mins:
            m.update(str(k).encode('utf-8'))
        return m.hexdigest()

    def name(self):
        if 'name' in self.d:
            return self.d.get('name')
        elif 'filename' in self.d:
            return self.d.get('filename')
        else:
            return self.md5sum()[:8]

    def save(self):
        e = dict(self.d)
        estimator = self.estimator

        sketch = {}
        sketch['ksize'] = int(estimator._kh.ksize())
        sketch['prime'] = estimator.p
        sketch['mins'] = list(map(int, estimator._mins))
        sketch['md5sum'] = self.md5sum()
        e['signature'] = sketch

        return self.d.get('email'), self.d.get('name'), \
               self.d.get('filename'), sketch

    def jaccard(self, other):
        return self.estimator.jaccard(other.estimator)


def load_signatures(data, select_ksize=None, ignore_md5sum=False):
    ## record header
    
    d = yaml.safe_load(data)
    if d.get('class') != 'sourmash_signature':
        raise Exception("incorrect class: %s" % d.get('class'))
    email = d['email']

    name = ''
    if 'name' in d:
        name = d['name']

    filename = ''
    if 'filename' in d:
        filename = d['filename']

    # one (old) or more (new) signatures
    if d.has_key('signature'):          # old
        assert d['version'] == '0.1'
        sketch = d['signature']
        sig = _load_one_signature(sketch, email, name, filename, ignore_md5sum)

        return [sig]
    elif d.has_key('signatures'):
        assert d['version'] == '0.2'

        siglist = []
        for sketch in d['signatures']:
            sig = _load_one_signature(sketch, email, name, filename,
                                      ignore_md5sum)
            if not select_ksize or select_ksize == sig.estimator.ksize:
                siglist.append(sig)
        return siglist


def _load_one_signature(sketch, email, name, filename, ignore_md5sum=False):
    ksize = sketch['ksize']
    prime = sketch['prime']
    mins = list(map(int, sketch['mins']))
    e = sourmash_lib.Estimators(ksize=ksize, max_prime=prime, n=0)
    e._mins = mins

    sig = SourmashSignature(email, e)
    if not ignore_md5sum:
        md5sum = sketch['md5sum']
        if md5sum != sig.md5sum():
            raise Exception('error loading - md5 of estimator does not match')

    if name:
        sig.d['name'] = name
    if filename:
        sig.d['filename'] = filename

    return sig


def save_signatures(siglist):
    top_records = {}
    for sig in siglist:
        email, name, filename, sketch = sig.save()
        if not email:
            raise Exception('email must be non-unique')
        k = (email, name, filename)
        
        x = top_records.get(k, [])
        x.append(sketch)
        top_records[k] = x

    if len(top_records) > 1: # not yet tested
        raise Exception("no support for multiple email/name/filename yet")

    for (email, name, filename), sketches in top_records.items():
        record = {}
        record['email'] = email
        if name:
            record['name'] = name
        if filename:
            record['filename'] = filename
        record['signatures'] = sketches

        record['version'] = '0.2'
        record['class'] = 'sourmash_signature'
        record['type'] = 'mrnaseq'
        
        return yaml.dump(record)
    
    assert 0

def test_roundtrip():
    e = sourmash_lib.Estimators()
    sig = SourmashSignature('titus@idyll.org', e)
    s = save_signatures([sig])
    siglist = load_signatures(s)
    sig2 = siglist[0]
    e2 = sig2.estimator
    
    assert e.jaccard(e2) == 1.0

def test_md5():
    e = sourmash_lib.Estimators()
    sig = SourmashSignature('titus@idyll.org', e)
    print(sig.save())
    assert sig.md5sum() == '9e1f3d700a7344f61db1d37fa11f60f2', sig.md5sum()