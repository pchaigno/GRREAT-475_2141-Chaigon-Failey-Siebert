#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test protodict implementation.

An Dict is a generic dictionary implementation which has keys of type
string, and values of varying types. The Dict can be used to serialize
and transport arbitrary python dictionaries containing a limited set of value.

Dict objects behave generally like a dict (with __getitem__, items() and
an __iter__) method, but are serializable as an RDFProto.
"""



from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr.lib.rdfvalues import test_base


class TestRDFValueArray(rdfvalue.RDFValueArray):
  rdf_type = rdfvalue.RDFString


class DictTest(test_base.RDFProtoTestCase):
  """Test the Dict implementation."""

  rdfvalue_class = rdfvalue.Dict

  def GenerateSample(self, number=0):
    return rdfvalue.Dict(foo=number, bar="hello")

  def CheckRDFValue(self, value, sample):
    super(DictTest, self).CheckRDFValue(value, sample)

    self.assertEqual(value.ToDict(), sample.ToDict())

  def CheckTestDict(self, test_dict, sample):
    for k, v in test_dict.items():
      # Test access through getitem.
      self.assertEqual(sample[k], v)

  def testDictBehaviour(self):
    tested = rdfvalue.Dict(a=1)

    now = rdfvalue.RDFDatetime().Now()
    tested["b"] = now

    self.assertEqual(tested["b"], now)
    self.assertEqual(tested["a"], 1)

    tested["b"] = rdfvalue.RDFURN("aff4:/users/")
    self.assertEqual(len(tested), 2)
    self.assertEqual(tested["b"].SerializeToString(), "aff4:/users")

  def testSerialization(self):
    test_dict = dict(
        key1=1,                # Integer.
        key2="foo",            # String.
        key3=u"\u4f60\u597d",  # Unicode.
        key5=rdfvalue.RDFDatetime("2012/12/11"),  # RDFValue.
        key6=None,             # Support None Encoding.
        key7=structs.Enum(5, name="Test"),  # Integer like objects.
        )

    # Initialize through keywords.
    sample = rdfvalue.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)

    # Initialize through dict.
    sample = rdfvalue.Dict(test_dict)
    self.CheckTestDict(test_dict, sample)

    # Initialize through a serialized form.
    serialized = sample.SerializeToString()
    self.assertIsInstance(serialized, str)

    sample = rdfvalue.Dict(serialized)
    self.CheckTestDict(test_dict, sample)

    # Convert to a dict.
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDicts(self):
    test_dict = dict(
        key1={"A": 1},
        key2=rdfvalue.Dict({"A": 1}),
        )

    sample = rdfvalue.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDictsMultipleTypes(self):
    test_dict = dict(
        key1={"A": 1},
        key2=rdfvalue.Dict({"A": 1}),
        key3=[1, 2, 3, [1, 2, [3]]],
        key4=[[], None, ["abc"]]
        )

    sample = rdfvalue.Dict(**test_dict)
    self.CheckTestDict(test_dict, sample)
    self.CheckTestDict(test_dict, sample.ToDict())

  def testNestedDictsOpaqueTypes(self):

    class UnSerializable(object):
      pass

    test_dict = dict(
        key1={"A": 1},
        key2=rdfvalue.Dict({"A": 1}),
        key3=[1, UnSerializable(), 3, [1, 2, [3]]],
        key4=[[], None, ["abc"]],
        key5=UnSerializable(),
        key6=["a", UnSerializable(), "b"]
        )

    self.assertRaises(TypeError, rdfvalue.Dict, **test_dict)

    sample = rdfvalue.Dict()
    for key, value in test_dict.iteritems():
      sample.SetItem(key, value, raise_on_error=False)

    # Need to do some manual checking here since this is a lossy conversion.
    self.assertEqual(test_dict["key1"], sample["key1"])
    self.assertEqual(test_dict["key2"], sample["key2"])

    self.assertEqual(1, sample["key3"][0])
    self.assertTrue("Unsupported type" in sample["key3"][1])
    self.assertItemsEqual(test_dict["key3"][2:], sample["key3"][2:])

    self.assertEqual(test_dict["key4"], sample["key4"])
    self.assertTrue("Unsupported type" in sample["key5"])
    self.assertEqual("a", sample["key6"][0])
    self.assertTrue("Unsupported type" in sample["key6"][1])
    self.assertEqual("b", sample["key6"][2])

  def testBool(self):
    sample = rdfvalue.Dict(a=True)
    self.assertTrue(isinstance(sample["a"], bool))
    sample = rdfvalue.Dict(a="true")
    self.assertEqual(sample["a"], "true")

  def testOverwriting(self):
    req = rdfvalue.Iterator(client_state=rdfvalue.Dict({"A": 1}))
    # There should be one element now.
    self.assertEqual(len(list(req.client_state.items())), 1)

    req.client_state = rdfvalue.Dict({"B": 2})
    # Still one element.
    self.assertEqual(len(list(req.client_state.items())), 1)

    req.client_state = rdfvalue.Dict({})

    # And now it's gone.
    self.assertEqual(len(list(req.client_state.items())), 0)


class RDFValueArrayTest(test_base.RDFProtoTestCase):
  """Test the Dict implementation."""

  rdfvalue_class = rdfvalue.RDFValueArray

  def GenerateSample(self, number=0):
    return rdfvalue.RDFValueArray([number])

  def testArray(self):
    sample = rdfvalue.RDFValueArray()

    # Add a string.
    sample.Append("hello")
    self.assertEqual(len(sample), 1)
    self.assertEqual(sample[0], "hello")

    # Add another RDFValue
    sample.Append(rdfvalue.RDFString("hello"))
    self.assertIsInstance(sample[1], rdfvalue.RDFString)

    # Test iterator.
    sample_list = list(sample)
    self.assertIsInstance(sample_list, list)
    self.assertIsInstance(sample_list[0], str)
    self.assertIsInstance(sample_list[1], rdfvalue.RDFString)

    # Test initialization from a list of variable types.
    test_list = [1, 2,   # Integers.
                 None,   # None.
                 rdfvalue.RDFDatetime().Now(),  # An RDFValue instance.
                 [1, 2],  # A nested list.
                 u"升级程序",  # Unicode.
                ]
    sample = rdfvalue.RDFValueArray(test_list)

    for x, y in zip(sample, test_list):
      self.assertEqual(x.__class__, y.__class__)
      self.assertEqual(x, y)

  def testEnforcedArray(self):
    """Check that arrays with a forced type are enforced."""
    sample = TestRDFValueArray()

    # Simple type should be coerced to an RDFString.
    sample.Append("hello")
    self.assertIsInstance(sample[0], rdfvalue.RDFString)

    # Reject appending invalid types.
    self.assertRaises(ValueError,
                      sample.Append, rdfvalue.RDFDatetime().Now())

  def testPop(self):
    sample = TestRDFValueArray()

    # Simple type should be coerced to an RDFString.
    sample.Append("hello")
    sample.Append("world")
    sample.Append("!")

    self.assertEqual(sample.Pop(), "hello")
    self.assertEqual(sample.Pop(1), "!")
    self.assertEqual(sample.Pop(), "world")


class EmbeddedRDFValueTest(test_base.RDFProtoTestCase):
  rdfvalue_class = rdfvalue.EmbeddedRDFValue

  def GenerateSample(self, number=0):
    return rdfvalue.EmbeddedRDFValue(rdfvalue.RDFValueArray([number]))

  def testAgePreserved(self):
    data = rdfvalue.RDFValueArray([1, 2, 3])
    now = rdfvalue.RDFDatetime().Now()
    original_age = data.age.Now()

    self.assertTrue((now - data.age) < rdfvalue.Duration("5s"))

    embedded = rdfvalue.EmbeddedRDFValue(payload=data)
    self.assertEqual(embedded.payload.age, original_age)

    new_log = rdfvalue.EmbeddedRDFValue(embedded).payload
    self.assertEqual(new_log.age, original_age, "Age not preserved: %s != %s" %
                     (new_log.age.AsMicroSecondsFromEpoch(),
                      original_age.AsMicroSecondsFromEpoch()))

