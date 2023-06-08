from kivy.uix.image import Image
from kivy.graphics import *
from kivy.uix.widget import Widget
from kivy.lang import Builder



Builder.load_file('style.kv')

class CircleImageView(Widget):
    def __init__(self, **kwargs):
        super(CircleImageView, self).__init__(**kwargs)
        with self.canvas:
            # create a stencil that defines the shape of the circle
            self.stencil = Ellipse(pos=self.pos, size=self.size)
            # set the stencil as the "mask" for the rectangle
            self.canvas.before.add(StencilPush())
            self.canvas.before.add(self.stencil)
            self.canvas.before.add(StencilUse())
            self.rect = Rectangle(pos=self.pos, size=self.size)
            self.canvas.before.add(self.rect)
            self.canvas.after.add(StencilUnUse())
            self.canvas.after.add(StencilPop())
            # bind the size and position of the widget to the stencil and rectangle
            self.bind(pos=self.update_stencil, size=self.update_stencil)

    def update_stencil(self, *args):
        # update the size and position of the stencil and rectangle
        self.stencil.pos = self.pos
        self.stencil.size = self.size
        self.rect.pos = self.pos
        self.rect.size = self.size