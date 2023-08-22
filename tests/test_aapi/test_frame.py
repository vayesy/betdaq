from betdaq.aapi.structures.fields import Int, Float, Str
from betdaq.aapi.structures.frame import Frame


class TestFrameClass:

    @classmethod
    def setup_class(cls):
        TestFrame = type('TestFrame', (Frame,), dict(
            test1=Int(order=1),
            test2=Float(order=2),
            test3=Str(order=3)
        ))
        cls.frame = TestFrame(test1=15, test2=15.01, test4='missing')

    def test_frame_str(self):
        assert str(self.frame) == 'TestFrame(...)'

    def test_frame_repr(self):
        assert repr(self.frame) == 'TestFrame(test1=15, test2=15.01)'


class TestEqual:

    def test_different_types(self):

        class TestFrame1(Frame):
            f1 = Int(order=1)

        class TestFrame2(Frame):
            f1 = Str(order=1)

        f1 = TestFrame1(f1=10)
        f2 = TestFrame2(f1='10')
        assert f1 != f2

    def test_same_types_different_values(self):

        class TestFrame(Frame):
            f1 = Int(order=1)

        f1 = TestFrame(f1=10)
        f2 = TestFrame(f1=11)
        assert f1 != f2

    def test_same_objects(self):

        class TestFrame(Frame):
            f1 = Str(order=1)

        f1 = TestFrame(f1='value')
        f2 = TestFrame(f1='value')
        assert f1 == f2
